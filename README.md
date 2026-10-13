# FreeCAD DIY tools

An independent FreeCAD add-on with a universal timber and plywood toolbar. The add-on lives in its own `DIYWorkbenchTools` folder; Woodworking updates do not replace these files.

## Compatibility and distribution

Version **0.6.2** targets **FreeCAD 1.1 or later**. Verification has used FreeCAD 1.1.3 on macOS; Windows, Linux and other FreeCAD versions are untested. Live mouse placement and OpenGL rendering still need manual checks on each platform.

This publication candidate is not listed in the public FreeCAD Addon Manager. Public release is pending the license and maintainer contact decisions. Use the manual installation below for an authorized local copy. See [publication status and checklist](docs/PUBLISHING.md) and [change history](CHANGELOG.md).

## Install on macOS, Linux or Windows

1. In FreeCAD, open **View → Panels → Python console** and run:

   ```python
   import FreeCAD
   print(FreeCAD.getUserAppDataDir())
   ```

2. The printed folder is your active FreeCAD user data folder. Its `Mod` subfolder is the installation location. Save your model and close FreeCAD. Back up any existing `Mod/DIYWorkbenchTools` folder, including your custom tools.
3. Extract the release ZIP or repository source archive. Copy its complete **`DIYWorkbenchTools` folder** into `Mod`. Keep that folder name and structure; `InitGui.py` must be at `Mod/DIYWorkbenchTools/InitGui.py`. Do not copy individual files directly into `Mod` or nest the whole source archive there.
4. Reopen FreeCAD and select a workbench. **DIY tools** appears below the other top toolbars and stays available across workbench changes.

Alternatively, from a complete checkout or extracted source archive, run:

```sh
python3 install.py --mod-root "/path/to/your/FreeCAD/user/data/Mod"
```

On Windows, use `py -3` if that is your Python command. Replace the example path with the `Mod` path found above. The installer overwrites matching `.py`, `.svg` and `.FCMacro` files in `DIYWorkbenchTools`; back up customizations first. It leaves unrelated files in that folder in place. Its default path is specific to macOS FreeCAD 1.1 (`~/Library/Application Support/FreeCAD/v1-1/Mod`), so use `--mod-root` for other profiles and platforms.

No DIY workbench selection is needed. The original Woodworking add-on and other workbench files remain unchanged.

## Show or hide

Use **Tools → DIY toolbar → Show DIY tools** to turn the row on or off. You can also use the toolbar visibility toggle. The choice is saved across workbench changes and restarts.

## Tools

Select one solid piece, then click **Auto Move** (blue cursor and green contact icon). The whole part follows the cursor immediately; no source corner or face click is needed. The separate **Auto snap** magnet button turns inferred connections on or off and remembers the choice. Auto Move and Auto snap are in the DIY toolbar and **Edit**. Rotate keeps its separate orange icon and angle controls.

- **Add timber / plywood:** Builder Depot PAR defaults: 4×2 = 94×44 mm, 3×2 = 69×44 mm, 3×4 = 94×69 mm. Plywood defaults to 18 mm thickness; enter finished cut length and depth. Sizes remain editable.
- **Move part:** keeps the original native 3D arrows and precision handles.
- **Auto Move:** the ghost preserves the point you picked, including nearby corners or edges. Aim at the destination face, edge or corner; Auto Move favours that object and keeps it during small cursor changes. A middle grip can align the nearby upper or lower side edge without moving to a distant beam end. A middle grip can also close a frame: nearby end boundaries snap even when the cursor is far from the joints. This fallback requires visible target boundaries, close world geometry (at most 50 mm) and close screen geometry; it cannot pull a part across hidden camera depth. Tree selection starts without a first-movement jump. Free movement uses a camera-facing plane; automatic contact uses visible target faces to resolve depth. Nearby matching timber ends align as a flush end-to-end extension; opposing faces and compatible edges/corners form butt or face contacts. Near a face boundary, Auto snap prefers a joint with both adjacent edges and planes flush. This extra alignment has a small capture range (up to the normal 18 screen pixels and 12 mm); away from boundaries, the piece can slide along the face. A guide marks the proposed contact and controls show XYZ movement and distance. Click once to place; Escape cancels. X/Y/Z lock movement; signed distance entry gives an exact axis move. Snap proposals preserve the angle and reject solid overlap and distant depth jumps. Snapping can be bypassed with the separate magnet button, S, or the Auto snap checkbox, including while a move is active. Ordinary free moves can overlap geometry when snapping is off. Each placement supports Undo. Native precision arrows remain available from Place & edit.
- **Place & edit:** size and angle display, cut length, position, rotation, visible size guide, mouse Transform, and planar face alignment. Mouse rotation defaults to 90° increments.
- **Join corners:** select one solid part, click its corner, then the destination corner. The nearest vertex is used.
- **Stand upright / Rotate X, Y, Z:** orient the selected part.

Old and new independent solid objects are supported. Select one object in the model tree. Folders and spreadsheets are not movable parts. Objects nested inside a Part or Body container are not supported. Cut length editing is for rectangular `Part::Box` objects; other solids can move and rotate. Face alignment centres faces and can leave overlapping geometry. It does not create permanent assembly constraints.

## Update or remove

Back up your existing `Mod/DIYWorkbenchTools` folder before updating, then follow the installation steps again with the new version. Keep custom tools in this add-on rather than editing Woodworking's `InitGui.py`.

To remove the add-on, close FreeCAD and move `Mod/DIYWorkbenchTools` outside `Mod`. Restart FreeCAD. Keep your backup until you are sure you no longer need it.

## Startup placeholder

On a fresh start in FreeCAD’s **<none>** placeholder, choose any workbench first. FreeCAD creates global command actions when a workbench loads. The row then remains available across workbench changes.

## Checks

`python3 -m unittest discover -s tests -v` checks startup, packaging and installation. `QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/Resources/bin/python tests/verify_qt_toolbar.py` checks real Qt row placement, delayed layout restoration and saved visibility (native toolbar creation is simulated). Automatic timber connection and lifecycle checks use `tests/verify_connection_snap.py`, `tests/verify_magnetic_geometry.py` and `tests/verify_qt_magnetic.py` with the same bundled Python (the GUI view boundary is simulated). Move/rotate and Undo can be checked with `QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/Resources/bin/python tests/verify_qt_move_rotate.py`. Geometry and editor controls can also be tested with the bundled Python using `tests/verify_geometry.py` and `tests/verify_qt_editor.py`. Rendering in the user's live OpenGL view requires a manual check.

## Dimension sources

- [Builder Depot 4×2 PAR](https://www.builderdepot.co.uk/50mm-x-100mm-planed-softwood-par-timber-4in-x-2in)
- [Builder Depot 3×2 PAR](https://www.builderdepot.co.uk/50mm-x-75mm-planed-softwood-par-timber-3in-x-2in)
- [Builder Depot 3×4 PAR](https://www.builderdepot.co.uk/75mm-x-100mm-planed-softwood-par-timber-4in-x-3in)

## Addon Manager custom source (after public release)

FreeCAD supports [repository-reference distribution](https://freecad.github.io/Addon-Academy/Guides/Publishing/Reference/) without an official Index listing. Once this repository is public, add `https://github.com/KSEGIT/freecad-diy-tools` to Addon Manager's custom repository settings. Select the released branch or tag rather than an older default-branch version. This publication candidate uses `codex/publish-diy-tools`; use manual installation if your Addon Manager does not offer that branch. Back up the existing manual installation first and avoid loading two copies. Custom-source installation has not yet been verified in this release review.

## Addon Manager package

`package.xml` describes this independent toolbar add-on. FreeCAD 1.1 loads the nested `InitGui.py` through its workbench content loader, but the extension registers no selectable workbench. This loader workaround is intentional. The manifest lacks a workbench class, and the add-on creates global toolbar/menu actions and changes `sys.path`; these need review against current Addon Index requirements before a listing request.

The package currently declares `UNLICENSED`. A license choice and public maintainer contact are still needed before public distribution. See [publication status](docs/PUBLISHING.md) for the remaining steps.

## Design references

The automatic movement flow follows whole-part connector matching, rather than requiring a manually picked source corner. [SketchUp Move](https://help.sketchup.com/en/sketchup/moving-entities-around) documents live grips, inference feedback, measurements and axis locks. [Autodesk Forge/APS drag-and-drop snapping](https://aps.autodesk.com/blog/drag-and-drop-snap-points) compares connectors on moving and placed models in screen space. This add-on generates timber connection features from the solids and checks contact/overlap locally in FreeCAD; no Autodesk service or SketchUp subscription is used.
