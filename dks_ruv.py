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
from typing import Iterable

import bpy
from bpy.types import Object
from bpy.utils import register_class, unregister_class


def _prefs():
    return bpy.context.preferences.addons[__package__].preferences


def _require_saved_file(operator) -> bool:
    if not bpy.data.is_saved:
        operator.report({"ERROR"}, "Please save the .blend file before using the RizomUV Bridge.")
        return False
    return True


def _export_directory() -> Path:
    prefs = _prefs()
    folder_name = prefs.option_export_folder.strip().strip("\\/") or "eXport"
    sanitized = bpy.path.clean_name(folder_name) or "eXport"
    base_path = Path(bpy.path.abspath("//"))
    export_dir = (base_path / sanitized).resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _export_filename(obj: Object) -> Path:
    clean_object_name = bpy.path.clean_name(obj.name) or obj.name
    return _export_directory() / f"{clean_object_name}_ruv.fbx"


def _prepare_object_mode(obj: Object) -> str:
    view_layer = bpy.context.view_layer
    if view_layer.objects.active is not obj:
        view_layer.objects.active = obj
    obj.select_set(True)
    previous_mode = obj.mode
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return previous_mode


def _restore_mode(obj: Object, previous_mode: str) -> None:
    if previous_mode and previous_mode != 'OBJECT':
        view_layer = bpy.context.view_layer
        if view_layer.objects.active is not obj:
            view_layer.objects.active = obj
        try:
            bpy.ops.object.mode_set(mode=previous_mode, toggle=False)
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


def _import_fbx(filepath: Path) -> Object:
    existing_names = {obj.name_full for obj in bpy.data.objects}
    result = bpy.ops.import_scene.fbx(filepath=str(filepath), axis_forward='-Z', axis_up='Y')
    if 'FINISHED' not in result:
        raise RuntimeError(f"Unable to import FBX file from RizomUV: {filepath}")

    new_objects = [obj for obj in bpy.data.objects if obj.name_full not in existing_names and obj.type == 'MESH']
    if not new_objects:
        raise RuntimeError("No mesh objects were imported from RizomUV.")

    return new_objects[0]


def _cleanup_import(objects: Iterable[Object]) -> None:
    for obj in objects:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


class dks_ruv_export(bpy.types.Operator):
    bl_idname = "dks_ruv.export"
    bl_label = "RizomUV"
    bl_description = "Export the current selection to RizomUV"

    @classmethod
    def poll(cls, context):
        active = context.view_layer.objects.active
        return active is not None and active.type == 'MESH'

    def execute(self, context):
        if not _require_saved_file(self):
            return {'CANCELLED'}

        if not context.selected_objects:
            self.report({'ERROR'}, "Select at least one object to export to RizomUV.")
            return {'CANCELLED'}

        prefs = _prefs()
        active = context.view_layer.objects.active
        previous_mode = _prepare_object_mode(active)
        export_file = _export_filename(active)

        if prefs.option_save_before_export:
            bpy.ops.wm.save_mainfile()

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

        _restore_mode(active, previous_mode)

        exe_path = Path(prefs.option_ruv_exe).expanduser()
        if not exe_path.is_file():
            self.report({'WARNING'}, f"FBX exported to {export_file}, but RizomUV executable was not found: {exe_path}")
            return {'FINISHED'}

        try:
            Popen([str(exe_path), str(export_file)])
        except OSError as exc:
            self.report({'WARNING'}, f"FBX exported, but RizomUV could not be launched: {exc}")

        return {'FINISHED'}


class dks_ruv_import(bpy.types.Operator):
    bl_idname = "dks_ruv.import"
    bl_label = "RizomUV"
    bl_description = "Import UVs from RizomUV back into the active object"

    @classmethod
    def poll(cls, context):
        active = context.view_layer.objects.active
        return active is not None and active.type == 'MESH'

    def execute(self, context):
        if not _require_saved_file(self):
            return {'CANCELLED'}

        active = context.view_layer.objects.active
        import_file = _export_filename(active)

        if not import_file.is_file():
            self.report({'ERROR'}, f"No RizomUV export found at {import_file}")
            return {'CANCELLED'}

        previous_mode = _prepare_object_mode(active)

        try:
            imported_obj = _import_fbx(import_file)
        except RuntimeError as exc:
            self.report({'ERROR'}, str(exc))
            _restore_mode(active, previous_mode)
            return {'CANCELLED'}

        try:
            _copy_uv_layers(imported_obj, active)
        except RuntimeError as exc:
            self.report({'ERROR'}, str(exc))
            bpy.context.view_layer.objects.active = active
            _cleanup_import([imported_obj])
            _restore_mode(active, previous_mode)
            return {'CANCELLED'}

        bpy.context.view_layer.objects.active = active
        _cleanup_import([imported_obj])

        active.select_set(True)
        bpy.context.view_layer.objects.active = active

        _restore_mode(active, previous_mode)
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
