# Blender Addon RizomUV

The RizomUV Bridge provides the user with an easy to use UI which makes transferring objects and UV maps between Blender and RizomUV as simple as clicking a button.

Seamless export and import between Blender and RizomUV, original objects are untouched, only UV data is transferred back to Blender.
Multiple UV sets support.

## Features

* One-click FBX export to RizomUV 2025 with safe defaults for Blender 4.x.
* Automatic round-trip import that transfers every UV map from RizomUV back to the active Blender mesh.
* Non-destructive workflow – only UV layers are updated, leaving your geometry and modifiers untouched.
* Configurable RizomUV executable path and export folder to match your pipeline.

## Requirements

* Blender 4.0 or newer (tested with Blender 4.5).
* RizomUV 2025 or newer.

## Usage Notes

* Save the `.blend` file before running an export. The add-on uses the file location to create the export directory and can optionally auto-save before each transfer.
* FBX files are named after the active object and stored in the configured export directory alongside the `.blend` file.

## Installation

Download the latest release archive from [https://github.com/DigiKrafting/blender_addon_rizom_uv/releases/latest](https://github.com/DigiKrafting/blender_addon_rizom_uv/releases/latest) and install it from *Edit → Preferences → Add-ons → Install...* in Blender.

## Screenshots

![Addon preferences showing RizomUV 2025 path](/screenshots/ruv_prefs.png)
![Export operator buttons](/screenshots/ruv_import.png)
![Imported UVs in Blender](/screenshots/ruv_imported.png)
![Toolbar buttons](/screenshots/ruv_btns.png)
![Topbar menu entry](/screenshots/ruv_menu.png)
![Standard workflow panel](/screenshots/ruv_standard.png)
