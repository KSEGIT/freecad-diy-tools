# Automatic Move implementation plan

**Goal:** Correct the rejected source-corner flow into select -> Move -> free cursor movement with inferred connections.
**Spec:** docs/superpowers/specs/2026-10-02-automatic-move-design.md
**Architecture:** Pure connection inference module using real Part faces/vertices/collision geometry; cursor session consumes proposed translated contact and existing safe Coin preview lifecycle. No new dependencies.

## Task 1 — connection inference
- [x] Test-first native geometry cases listed in acceptance; capture failing missing-feature run.
- [x] Create WorkbenchConnectionSnap.py with connection_snap(source_shape, target_shapes, raw_delta, project, tolerance_px=18, world_tolerance=50, axis=None, previous=None)->dict or None. target_shapes=list[(label,world_shape)]. Result keys delta, source, target (App.Vector), label, kind, key. source/target are contact points before/after translation. Project(point)->pixel(x,y). Optional previous prior result provides hysteresis.
- [x] Generate face centre extension candidates for matching end profiles, opposing planar face contact candidates retaining in-plane movement, and compatible face/corner candidates. Screen+world proximity and axis compatibility constrain correction. Reject positive-volume intersection against targets. Prioritize correct extension, then sensible flush/contact/corner; do not rotate. Prune near pairs before expensive collision checks. Verify and commit owned files.

## Task 2 — immediate movement
- [x] Test-first source-centre initialization, first motion and placement without a source click, connections/guide, keyboard/S bypass, exact axis distance, cleanup and Undo.
- [x] Refactor WorkbenchMagneticMove.py into automatic cursor flow using connection_snap; preserve existing lifecycle protections. Compact controls positioned at window edge. Ghost appears at start. Original model remains untouched until commit. Target snapshots refresh with geometry/visibility changes. Determine world tolerance from current camera scale with a finite cap. Source/targets native picking visibility rules retained.
- [x] Wire DIY_MovePart to this automatic flow; legacy DIY_MagneticMove is a separate persistent Auto snap toggle. Preserve Rotate and precision transform in Place & edit. Update verify_qt_magnetic.py and verify_qt_move_rotate.py accordingly. Worker owns these four files, not toolbar/icon/docs. Commit after checks.

## Task 3 — toolbar and finish
- [x] Move starts automatic movement; separate checkable magnet button toggles the shared saved SnapEnabled state. Edit menu shares both actions; preserve their existing command IDs. Update real Qt migration tests, docs and package0.5.0.
- [x] Fresh review inference and full interaction. Run standard8, native geometry, Qt interaction/toolbar/MoveRotate/editor, compile and diff checks. Fix blockers.
- [x] Install verified add-on without changing Woodworking, push feature/update existing PR, preserve local source and remove worktree. Live native rendering is unverified if computer use remains unavailable; state this explicitly.

## Verification record

Fresh geometry and whole-feature reviewers found no blocking issues. Final checks on 2026-10-02: standard unittest discovery 8 passed; verify_connection_snap.py 12 passed; verify_qt_magnetic.py 29 passed; verify_magnetic_geometry.py 7 passed; verify_qt_toolbar.py 9 passed. verify_qt_move_rotate.py, verify_geometry.py and verify_qt_editor.py passed. Bundled FreeCAD Python compileall and git diff --check passed. Native geometry, Qt and Coin were tested with simulated view boundaries. Live OpenGL rendering and native mouse dispatch remain unverified because computer control timed out.

Installation: 20 installed source files match byte-for-byte; 159 original Woodworking file signatures unchanged. Feature is published through the existing pull request; local source is retained before worktree cleanup.
