# FreeCAD DIY tools

An independent FreeCAD add-on with a universal timber and plywood toolbar. The add-on lives in its own `DIYWorkbenchTools` folder; Woodworking updates do not replace these files.

## Install on this Mac

Save the model and close FreeCAD. Run `python3 install.py`, then reopen FreeCAD. **DIY tools** appears as the last row below the other top toolbars in every workbench. The default install folder is `~/Library/Application Support/FreeCAD/v1-1/Mod/DIYWorkbenchTools`. Use `--mod-root` to choose another FreeCAD profile.

No workbench selection is needed. The original Woodworking add-on and other workbench files remain unchanged.

## Show or hide

Use **Tools → DIY toolbar → Show DIY tools** to turn the row on or off. You can also use the toolbar visibility toggle. The choice is saved across workbench changes and restarts.

## Tools

Select one solid piece in the model tree, then use the **Move part** (blue arrows) or **Rotate part** (orange curved arrow) buttons. Both also appear directly in **Edit**. Move opens the native cursor handles; Rotate lets you choose X/Y/Z and enter an angle, then Apply. Each rotation supports Undo.

- **Add timber / plywood:** Builder Depot PAR defaults: 4×2 = 94×44 mm, 3×2 = 69×44 mm, 3×4 = 94×69 mm. Plywood defaults to 18 mm thickness; enter finished cut length and depth. Sizes remain editable.
- **Place & edit:** size and angle display, cut length, position, rotation, visible size guide, mouse Transform, and planar face alignment. Mouse rotation defaults to 90° increments.
- **Join corners:** select one solid part, click its corner, then the destination corner. The nearest vertex is used.
- **Stand upright / Rotate X, Y, Z:** orient the selected part.

Old and new independent solid objects are supported. Select one object in the model tree. Folders and spreadsheets are not movable parts. Objects nested inside a Part or Body container are not supported. Cut length editing is for rectangular `Part::Box` objects; other solids can move and rotate. Face alignment centres faces and can leave overlapping geometry. It does not create permanent assembly constraints.

## Recover after an update

Run `python3 install.py` again from this repository. The original standalone source copies in the parent DIY folder are also preserved. Keep custom tools in this add-on rather than editing Woodworking's `InitGui.py`.

## Startup placeholder

On a fresh start in FreeCAD’s **<none>** placeholder, choose any workbench first. FreeCAD creates global command actions when a workbench loads. The row then remains available across workbench changes.

## Checks

`python3 -m unittest discover -s tests -v` checks startup, packaging and installation. `QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/Resources/bin/python tests/verify_qt_toolbar.py` checks real Qt row placement, delayed layout restoration and saved visibility (native toolbar creation is simulated). Move/rotate and Undo can be checked with `QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/Resources/bin/python tests/verify_qt_move_rotate.py`. Geometry and editor controls can also be tested with the bundled Python using `tests/verify_geometry.py` and `tests/verify_qt_editor.py`. Rendering in the user's live OpenGL view requires a manual check.

## Dimension sources

- [Builder Depot 4×2 PAR](https://www.builderdepot.co.uk/50mm-x-100mm-planed-softwood-par-timber-4in-x-2in)
- [Builder Depot 3×2 PAR](https://www.builderdepot.co.uk/50mm-x-75mm-planed-softwood-par-timber-3in-x-2in)
- [Builder Depot 3×4 PAR](https://www.builderdepot.co.uk/75mm-x-100mm-planed-softwood-par-timber-4in-x-3in)

## Addon Manager package

`package.xml` describes this independent toolbar add-on. FreeCAD 1.1 loads the nested `InitGui.py` through its workbench content loader, but the extension registers no selectable workbench. The repository is private and is not in the public Addon Manager list. Public distribution would need a license choice, maintainer contact, and listing review. The installer works now without that listing.
