# Auto Move depth and pickup repair

Screenshots showed the upright failing to meet the rail and unexpected movement. Read-only native FreeCAD API inspection confirmed valid target points can differ from the fixed movement plane by 238 mm. Independent real Coin/Part reproduction: an intended joint and free preview project to the same pixel yet differ by 198.61 mm. Raising the old 50 mm capture limit to 300 mm still selects the wrong closer side contact.

Preserve the existing Move part command. Auto Move preserves native SelectionEx.PickedPoints; when tree selection provides none, the first cursor event establishes a zero-delta baseline. Infer depth from native visible face hits sampled at moving timber features, not arbitrary hidden geometry. Prioritise contact with those faces while retaining finite surface/collision validation, pixel capture and axis restrictions. Preserve angle and Undo.

Implementer tasks: geometry adds visible depth-face candidates with camera-ray direction; UI acquires pickup and native hit-face constraints. Review the combined change and run native Coin/Part and Qt regression tests, then verify against the actual live camera through the local API. Install independently, update existing feature PR, retain local source and remove worktree. No Woodworking changes or new dependencies.

Review repair: rejected contact candidates remain collision obstacles. Retry excludes a single candidate key instead of removing a complete target solid, which also preserves other valid faces on that solid. Source feature probes include all six box face centres. Test runners must restore the checkout path after FreeCAD initialises its installed Mod paths.

## Verified result

Fresh review approved the combined repair. Native bundled tests: verify_connection_snap.py 18 passed; verify_qt_magnetic.py 36 passed; verify_magnetic_geometry.py 7 passed; verify_qt_toolbar.py 9 passed. Standard unittest discovery 8 passed. Move/Rotate, geometry and editor checks passed. compileall and git diff --check passed.

Read-only integration used the active FreeCAD camera and WorkbenchPiece003/WorkbenchPiece002 shapes, without altering document placements or active tool. A required depth correction of 351.37 mm resolves to visible rail Face6. The upright end contacts 4136 mm² (44×94 mm), with zero gap, zero overlap volume and exact rail-width alignment. Native screen mouse dispatch remains unverified; current framebuffer capture and native face picking were available through the local FreeCAD API.

Installation: 21 source files verified byte-for-byte; original 159 Woodworking file signatures unchanged.
