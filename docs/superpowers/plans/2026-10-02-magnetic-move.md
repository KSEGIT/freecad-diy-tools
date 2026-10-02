# Magnetic Move Implementation Plan

**Goal:** Cursor movement with exact snap previews, axis locks, visible dimensions and Undo.
**Architecture:** Isolate FreeCAD geometry/snap decisions from a Qt/Coin event session. Use a separate command in the existing universal toolbar and Edit menu.
**Tech Stack:** FreeCAD 1.1.3, bundled PySide and pivy; no dependencies added.
**Spec:** docs/superpowers/specs/2026-10-02-magnetic-move-design.md

## Constraints and review focus
Preserve original Woodworking and existing normal Move. Work only in this worktree. Test-first geometry and UI boundary tests. Test rotated solids, zoom/pixel tolerance, ambiguous targets, hidden/source exclusion, axis conflict, cancellation, removed objects, closed/switching documents, callback removal, exact placement and Undo. Native rendering requires a separate live check.

## Task 1: Snap geometry
- [x] Create tests/verify_magnetic_geometry.py using real FreeCAD/Part geometry. Watch failure before implementation.
- [x] Create DIYWorkbenchTools/WorkbenchMagneticGeometry.py with candidate tuples (kind, world_point, label), functions shape_candidates(shape,label), choose_snap(candidates,cursor,project,tolerance=14,anchor=None,axis=None), constrained_point(point,anchor,axis=None), translated_placement(original,anchor,destination). Document returned types.
- [x] Corners and straight-edge midpoints only; planar picked face supplied separately by session. Screen projection controls tolerance; incompatible locked-axis candidates excluded. Never modify objects in helpers.
- [x] Verify native bundled Python tests. Commit owned files.

## Task 2: Magnetic interaction
- [x] Create tests/verify_qt_magnetic.py with real Qt/Coin/FreeCAD and a fake view only at the GUI boundary. Watch initial missing-feature failure.
- [x] Create DIYWorkbenchTools/WorkbenchMagneticMove.py with command DIY_MagneticMove and a modeless compact MagneticMoveDialog/session. Select source corner, show live unpickable ghost of solid, target marker and guides; placement commit only on click or exact-axis Apply. Live label includes target/delta/distance, axis buttons and distance field. Escape cancels; callbacks consume intended clicks but preserve navigation buttons.
- [x] Use verified FreeCAD 1.1.3 APIs from official source/docs before coding. Source shape world coordinates; camera projection/focal plane verified. Cache target corner/midpoint geometry; refresh when document changes and pick planar face under cursor. Screen tolerance uses actual projected pixels.
- [x] Clean all callbacks/Coin nodes on close, cancel, document/view switch, removal and command reentry. Single Undo transaction on commit, no model preview mutations.
- [x] Verify geometry/UI regression checks and commit owned files. Do not modify toolbar integration (controller owns).

## Task 3: Integration and review
- [x] Add differentiated magnet SVG, register module/command in toolbar and Edit, add toolbar regression assertions, docs and metadata version.
- [x] Run standard unittest, native geometry, Qt interaction and existing Qt/geometry suites plus compile and whitespace checks.
- [x] Fresh reviewer checks entire feature, fix defects, repeat affected checks.
- [x] Install verified files without touching Woodworking; push feature branch/open PR; attach PR; remove worktree after preserving source changes.

## Verification record

Geometry task reviewed independently; no blocking findings. Full feature review found one command reentry cleanup defect, fixed in38a9858 and approved after scoped re-review. Final interaction24, geometry7, toolbar8, standard8 passed. Existing Move/Rotate, geometry and editor checks passed. Compilation and whitespace checks passed. Qt offscreen font/size-hint warnings are environment limitations. Live OpenGL rendering was unavailable because computer use timed out; test views are simulated with real FreeCAD geometry, Qt and Coin. Native FreeCAD and Woodworking are not modified.
