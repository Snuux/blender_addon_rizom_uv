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

bl_info = {
        "name": "DKS RizomUV",
        "description": (
                "Bridge Blender and RizomUV with an intuitive one-click workflow. "
                "Export meshes, unwrap them in RizomUV, and bring every UV set back "
                "without disturbing the original objects."
        ),
        "author": "DigiKrafting.Studio, Snuux",
        "version": (1, 0, 0),
        "blender": (4, 0, 0),
        "location": "File -> Import, File -> Export",
        "wiki_url":    "https://github.com/DigiKrafting/blender_addon_rizom_uv/wiki",
        "tracker_url": "https://github.com/DigiKrafting/blender_addon_rizom_uv/issues",
        "category": "Import-Export",
}

from pathlib import Path
import tempfile

import bpy
from bpy.utils import register_class, unregister_class
from . import dks_ruv


def _ui_export_directory():

        getter = getattr(dks_ruv, "get_export_directory", None)
        if callable(getter):
                return getter()

        legacy_getter = getattr(dks_ruv, "_export_directory", None)
        if callable(legacy_getter):
                return legacy_getter()

        fallback = Path(tempfile.gettempdir()) / getattr(dks_ruv, "EXPORT_SUBDIR_NAME", "rizomuv_bridge")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


class DKS_RUV_OT_open_export_directory(bpy.types.Operator):

        bl_idname = "dks_ruv.open_export_directory"
        bl_label = "Open Export Folder"
        bl_description = "Open the temporary folder used for RizomUV transfers"

        def execute(self, context):

                export_dir = _ui_export_directory()
                try:
                        export_dir.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                        self.report({'ERROR'}, f"Unable to prepare the export folder: {exc}")
                        return {'CANCELLED'}

                result = bpy.ops.wm.path_open(filepath=str(export_dir))
                if 'CANCELLED' in result:
                        self.report({'ERROR'}, "Blender could not open the export folder.")
                        return {'CANCELLED'}

                return {'FINISHED'}


class dks_ruv_addon_prefs(bpy.types.AddonPreferences):

        bl_idname = __package__

        option_ruv_exe : bpy.props.StringProperty(
                name="RizomUV Executable",
                subtype='FILE_PATH',
                default=r"C:\Program Files\Rizom Lab\RizomUV 2025.0\rizomuv.exe",
        )
        option_export_folder : bpy.props.StringProperty(
                name="Custom Export Folder",
                description=(
                        "Optional folder that overrides the temporary export "
                        "location. Leave empty to use Blender's temporary "
                        "directory."
                ),
                subtype='DIR_PATH',
                default="",
        )
        def draw(self, context):

                layout = self.layout

                box = layout.box()
                box.prop(self, 'option_ruv_exe')

                box = layout.box()
                box.label(text="Export folder:")
                box.prop(self, 'option_export_folder')

                try:
                        export_dir = _ui_export_directory()
                except Exception as exc:  # pragma: no cover - UI feedback only
                        box.label(text="Unable to determine folder", icon='ERROR')
                        box.label(text=str(exc))
                else:
                        box.label(text=str(export_dir), icon='FILE_FOLDER')
                        box.operator("dks_ruv.open_export_directory", icon='FILEBROWSER')
def dks_ruv_menu_func_export(self, context):
    self.layout.operator("dks_ruv.export")

def dks_ruv_menu_func_import(self, context):
    self.layout.operator("dks_ruv.import")

classes = (
    DKS_RUV_OT_open_export_directory,
    dks_ruv_addon_prefs,
)

def register():

    for cls in classes:
        register_class(cls)

    dks_ruv.register()

    bpy.types.TOPBAR_MT_file_export.append(dks_ruv_menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(dks_ruv_menu_func_import)

def unregister():

    bpy.types.TOPBAR_MT_file_import.remove(dks_ruv_menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(dks_ruv_menu_func_export)

    dks_ruv.unregister()

    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":

    register()
