# Release Notes

## 1.1.0 – Selection-aware RizomUV Link
- Export workflow now scopes to the currently selected mesh objects and automatically restores Blender's selection and mode state once the FBX is written.
- Added RizomUVLink integration that reuses an already-open RizomUV window when possible and launches RizomUV when no session is active.
- Persisted export metadata so UV imports are applied back to the meshes that originated the export, even if the user changes the selection later.

## 1.0.0 – Blender 4.x refresh
- Updated default RizomUV path and temporary export handling for 2025 releases.
- Added a quick-access button to open the export folder directly from the preferences.
- Improved documentation and metadata to better describe the round-trip workflow.

## 0.9.0 – Initial public release
- First stable bridge between Blender and RizomUV with one-click export/import.
- Support for multiple UV maps and safe non-destructive updates.
- Added toolbar buttons and menu entries for both exporting and importing UVs.
