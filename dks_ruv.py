# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

from __future__ import annotations

from pathlib import Path
from subprocess import Popen
from typing import Dict, Iterable, List, Optional, Tuple

import json
import tempfile

import bpy
from bpy.types import Object
from bpy.utils import register_class, unregister_class


try:  # Optional RizomUV Link integration
    from RizomUVLink import CRizomUVLink, CZEx  # type: ignore
except Exception:  # pragma: no cover - optional dependency, may not exist
    CRizomUVLink = None  # type: ignore
    CZEx = RuntimeError  # type: ignore


EXPORT_SUBDIR_NAME = "rizomuv_bridge"


def _prefs():
    return bpy.context.preferences.addons[__package__].preferences


def _require_saved_file(operator) -> bool:
    if not bpy.data.is_saved:
        operator.report({"ERROR"}, "Please save the .blend file before using the RizomUV Bridge.")
        return False
    return True


def get_export_directory() -> Path:
    """Return the export directory used for RizomUV transfers.

    The folder is always located inside the operating system's temporary
    directory (or Blender's override, if available) to avoid accidental exports
    to arbitrary user-specified locations. The directory is created on demand
    and a stable location is returned for the duration of the Blender session.
    """

    candidate_roots: List[Path] = []

    blender_temp = getattr(bpy.app, "tempdir", None)
    if blender_temp:
        candidate_roots.append(Path(blender_temp))

    system_temp = Path(tempfile.gettempdir())
    if system_temp not in candidate_roots:
        candidate_roots.append(system_temp)

    for root in candidate_roots:
        target_dir = root / EXPORT_SUBDIR_NAME
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        else:
            return target_dir

    # As a last resort, create a dedicated temporary directory that is unique
    # to the current invocation.
    fallback_dir = Path(tempfile.mkdtemp(prefix=f"{EXPORT_SUBDIR_NAME}_"))
    return fallback_dir


def _export_directory() -> Path:
    return get_export_directory()


def _export_filename(obj: Object) -> Path:
    clean_object_name = bpy.path.clean_name(obj.name) or obj.name
    return _export_directory() / f"{clean_object_name}_ruv.fbx"


def _selection_snapshot(context) -> Tuple[Dict[str, bool], Optional[Object]]:
    scene = context.scene
    selection = {obj.name: obj.select_get() for obj in scene.objects}
    active = context.view_layer.objects.active
    return selection, active


def _restore_selection(context, selection: Dict[str, bool], active: Optional[Object]) -> None:
    scene = context.scene
    for obj in scene.objects:
        obj.select_set(selection.get(obj.name, False))
    if active:
        restored_active = scene.objects.get(active.name)
        context.view_layer.objects.active = restored_active
    else:
        context.view_layer.objects.active = None


def _ensure_objects_object_mode(context, objects: Iterable[Object]) -> Dict[str, str]:
    view_layer = context.view_layer
    previous_modes: Dict[str, str] = {}
    for obj in objects:
        if obj.mode != 'OBJECT':
            view_layer.objects.active = obj
            previous_modes[obj.name] = obj.mode
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return previous_modes


def _restore_object_modes(context, previous_modes: Dict[str, str]) -> None:
    view_layer = context.view_layer
    for obj_name, mode in previous_modes.items():
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            continue
        view_layer.objects.active = obj
        try:
            bpy.ops.object.mode_set(mode=mode, toggle=False)
        except RuntimeError:
            pass


def _ensure_uv_topology_matches(source: Object, target: Object) -> None:
    if source.type != 'MESH' or target.type != 'MESH':
        raise RuntimeError("RizomUV import requires mesh objects.")

    src_mesh = source.data
    dst_mesh = target.data

    if len(src_mesh.vertices) != len(dst_mesh.vertices) or len(src_mesh.loops) != len(dst_mesh.loops):
        raise RuntimeError("Imported mesh topology does not match the active object.")


def _copy_uv_layers(source: Object, target: Object) -> None:
    _ensure_uv_topology_matches(source, target)

    src_mesh = source.data
    dst_mesh = target.data

    while dst_mesh.uv_layers:
        dst_mesh.uv_layers.remove(dst_mesh.uv_layers[0])

    if not src_mesh.uv_layers:
        dst_mesh.update()
        return

    for src_layer in src_mesh.uv_layers:
        dst_layer = dst_mesh.uv_layers.new(name=src_layer.name)
        for loop_index, src_data in enumerate(src_layer.data):
            dst_layer.data[loop_index].uv = src_data.uv

    if src_mesh.uv_layers.active_index >= 0:
        dst_mesh.uv_layers.active_index = src_mesh.uv_layers.active_index

    if hasattr(src_mesh.uv_layers, "active_render_index") and src_mesh.uv_layers.active_render_index >= 0:
        dst_mesh.uv_layers.active_render_index = src_mesh.uv_layers.active_render_index

    if hasattr(src_mesh.uv_layers, "active_clone_index") and src_mesh.uv_layers.active_clone_index >= 0:
        dst_mesh.uv_layers.active_clone_index = src_mesh.uv_layers.active_clone_index

    dst_mesh.update()


def _import_fbx(filepath: Path) -> List[Object]:
    existing_names = {obj.name_full for obj in bpy.data.objects}
    result = bpy.ops.import_scene.fbx(filepath=str(filepath), axis_forward='-Z', axis_up='Y')
    if 'FINISHED' not in result:
        raise RuntimeError(f"Unable to import FBX file from RizomUV: {filepath}")

    new_objects = [obj for obj in bpy.data.objects if obj.name_full not in existing_names and obj.type == 'MESH']
    if not new_objects:
        raise RuntimeError("No mesh objects were imported from RizomUV.")

    return new_objects


def _cleanup_import(objects: Iterable[Object]) -> None:
    for obj in objects:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def _state_file() -> Path:
    return _export_directory() / "last_export.json"


def _load_state() -> Dict[str, object]:
    path = _state_file()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: Dict[str, object]) -> None:
    path = _state_file()
    try:
        with path.open("w", encoding="utf8") as handle:
            json.dump(state, handle, indent=2)
    except OSError:
        pass


def _connect_or_launch_rizom(exe_path: Path, state: Dict[str, object]):
    if CRizomUVLink is None:
        return None

    link = CRizomUVLink()
    port = state.get("port")
    if isinstance(port, int):
        try:
            link.Connect(port)
            return link
        except Exception:
            port = None

    try:
        port = link.RunRizomUV(str(exe_path))
    except CZEx:  # type: ignore[misc]
        return None
    except Exception:
        return None

    state["port"] = port
    _save_state(state)
    return link


def _send_to_rizom(exe_path: Path, export_file: Path, operator, state: Dict[str, object]) -> None:
    link = _connect_or_launch_rizom(exe_path, state)
    if link is not None:
        try:
            link.Load({"File": {"Path": str(export_file)}})
            return
        except Exception as exc:
            operator.report({'WARNING'}, f"Unable to communicate with RizomUV instance: {exc}")

    try:
        Popen([str(exe_path), str(export_file)])
    except OSError as exc:
        operator.report({'WARNING'}, f"FBX exported, but RizomUV could not be launched: {exc}")


class dks_ruv_export(bpy.types.Operator):
    bl_idname = "dks_ruv.export"
    bl_label = "RizomUV"
    bl_description = "Export the current selection to RizomUV"

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        if not _require_saved_file(self):
            return {'CANCELLED'}

        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_meshes:
            self.report({'ERROR'}, "Select at least one mesh object to export to RizomUV.")
            return {'CANCELLED'}

        prefs = _prefs()
        state = _load_state()

        selection_snapshot = _selection_snapshot(context)
        mode_snapshot = _ensure_objects_object_mode(context, selected_meshes)

        active = context.view_layer.objects.active
        if active not in selected_meshes:
            active = selected_meshes[0]
        export_file = (_export_filename(active) if len(selected_meshes) == 1 else (_export_directory() / "selection_ruv.fbx"))

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_meshes:
            obj.select_set(True)
        context.view_layer.objects.active = active

        bpy.ops.export_scene.fbx(
            filepath=str(export_file),
            use_selection=True,
            check_existing=False,
            axis_forward='-Z',
            axis_up='Y',
            apply_unit_scale=True,
            add_leaf_bones=False,
            use_custom_props=False,
            bake_anim=False,
            use_mesh_modifiers=True,
        )

        _restore_object_modes(context, mode_snapshot)
        _restore_selection(context, *selection_snapshot)

        exe_path = Path(prefs.option_ruv_exe).expanduser()
        if not exe_path.is_file():
            self.report({'WARNING'}, f"FBX exported to {export_file}, but RizomUV executable was not found: {exe_path}")
            return {'FINISHED'}

        state.update({
            "objects": [obj.name for obj in selected_meshes],
            "filepath": str(export_file),
        })
        _save_state(state)

        _send_to_rizom(exe_path, export_file, self, state)

        return {'FINISHED'}


class dks_ruv_import(bpy.types.Operator):
    bl_idname = "dks_ruv.import"
    bl_label = "RizomUV"
    bl_description = "Import UVs from RizomUV back into the active object"

    @classmethod
    def poll(cls, context):
        state = _load_state()
        if not state.get("objects"):
            return False
        for name in state.get("objects", []):
            obj = bpy.data.objects.get(name)
            if obj and obj.type == 'MESH':
                return True
        return False

    def execute(self, context):
        if not _require_saved_file(self):
            return {'CANCELLED'}

        state = _load_state()
        export_objects = [bpy.data.objects.get(name) for name in state.get("objects", [])]
        export_objects = [obj for obj in export_objects if obj and obj.type == 'MESH']
        if not export_objects:
            self.report({'ERROR'}, "No previous RizomUV export found for the current scene.")
            return {'CANCELLED'}

        import_path = state.get("filepath")
        if import_path:
            import_file = Path(import_path)
        else:
            active = context.view_layer.objects.active
            if not active or active.type != 'MESH':
                self.report({'ERROR'}, "Unable to determine which RizomUV export to import.")
                return {'CANCELLED'}
            import_file = _export_filename(active)

        if not import_file.is_file():
            self.report({'ERROR'}, f"No RizomUV export found at {import_file}")
            return {'CANCELLED'}

        selection_snapshot = _selection_snapshot(context)
        mode_snapshot = _ensure_objects_object_mode(context, export_objects)

        try:
            imported_objects = _import_fbx(import_file)
        except RuntimeError as exc:
            self.report({'ERROR'}, str(exc))
            _restore_object_modes(context, mode_snapshot)
            _restore_selection(context, *selection_snapshot)
            return {'CANCELLED'}

        imported_by_name = {obj.name: obj for obj in imported_objects}
        updated_targets: List[Object] = []
        for target in export_objects:
            source = imported_by_name.get(target.name)
            if not source:
                self.report({'WARNING'}, f"Imported data for '{target.name}' was not found.")
                continue
            try:
                _copy_uv_layers(source, target)
            except RuntimeError as exc:
                self.report({'ERROR'}, str(exc))
                _cleanup_import(imported_objects)
                _restore_object_modes(context, mode_snapshot)
                _restore_selection(context, *selection_snapshot)
                return {'CANCELLED'}
            updated_targets.append(target)

        _cleanup_import(imported_objects)

        if updated_targets:
            for obj in updated_targets:
                obj.data.update()

        _restore_object_modes(context, mode_snapshot)
        _restore_selection(context, *selection_snapshot)

        return {'FINISHED'}


classes = (
    dks_ruv_import,
    dks_ruv_export,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
