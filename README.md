# Blender Addon RizomUV

The RizomUV Bridge gives Blender artists a friendly, human-readable workflow for sending meshes to RizomUV and bringing the finished UVs back home. In just a couple of clicks you can launch RizomUV from inside Blender, unwrap your assets, and return to shading work with confidence.

Seamless export and import between Blender and RizomUV keeps your original objects untouched—only the UV data is updated on the way back. The add-on understands multiple UV sets, so every map you tweak in RizomUV is restored automatically inside Blender.

## Features

* One-click FBX export to RizomUV 2025 with safe defaults for Blender 4.x.
* Automatically reconnects to an existing RizomUV session when available, or launches RizomUV for you when it's closed.
* Automatic round-trip import that transfers every UV map from RizomUV back to the active Blender mesh.
* Non-destructive workflow – only UV layers are updated, leaving your geometry and modifiers untouched.
* Configurable RizomUV executable path, defaulting to `C:\Program Files\Rizom Lab\RizomUV 2025.0\rizomuv.exe` for fresh installs.
* Cross-platform temporary export folder that lives in your operating system's temp directory, with a handy “Open Export Folder” button in the add-on preferences.

## Requirements

* Blender 4.0 or newer (tested with Blender 4.5).
* RizomUV 2025 or newer.

## Usage Notes

* Save the `.blend` file before running an export. The add-on still requires a saved project so that Blender can safely trigger the round-trip.
* FBX files are named after the active object and stored in a dedicated RizomUV Bridge folder inside your system's temporary directory.
* Only the currently selected mesh objects are exported, and your Blender selection/mode state is restored automatically afterwards.

## Installation

Download the latest release archive from [https://github.com/DigiKrafting/blender_addon_rizom_uv/releases/latest](https://github.com/DigiKrafting/blender_addon_rizom_uv/releases/latest) and install it from *Edit → Preferences → Add-ons → Install...* in Blender.

## Release Notes

### 1.1.0 – Selection-aware RizomUV Link
* Export only the currently selected mesh objects while keeping Blender's selection and mode intact.
* Reuse active RizomUV windows through RizomUVLink and launch RizomUV automatically when it's not running.
* Store export metadata to ensure imported UVs are applied back to the original meshes regardless of the current selection.

### 1.0.0 – Blender 4.x refresh
* Updated default RizomUV path and temporary export handling for 2025 releases.
* Added a quick-access button to open the export folder directly from the preferences.
* Improved documentation and metadata to better describe the round-trip workflow.

### 0.9.0 – Initial public release
* First stable bridge between Blender and RizomUV with one-click export/import.
* Support for multiple UV maps and safe non-destructive updates.
* Added toolbar buttons and menu entries for both exporting and importing UVs.
