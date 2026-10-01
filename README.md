# FreeCAD DIY tools

A separate FreeCAD workbench for timber and plywood. The add-on lives in its own `DIYWorkbenchTools` folder; Woodworking updates do not replace these files.

## Install on this Mac

Save the model and close FreeCAD. Run `python3 install.py`, then reopen FreeCAD and select **DIY tools**. The default install folder is `~/Library/Application Support/FreeCAD/v1-1/Mod/DIYWorkbenchTools`. Use `--mod-root` to choose another FreeCAD profile.

The DIY tools have their own top toolbar row and a **DIY tools** menu. No vendor files are modified.

## Tools

- **Add timber / plywood:** Builder Depot PAR defaults: 4×2 = 94×44 mm, 3×2 = 69×44 mm, 3×4 = 94×69 mm. Plywood defaults to 18 mm thickness; enter finished cut length and depth. Sizes remain editable.
- **Place & edit:** size and angle display, cut length, position, rotation, visible size guide, mouse Transform, and planar face alignment. Mouse rotation defaults to 90° increments.
- **Join corners:** select one solid part, click its corner, then the destination corner. The nearest vertex is used.
- **Stand upright / Rotate X, Y, Z:** orient the selected part.

Old and new independent solid objects are supported. Select one object in the model tree. Folders and spreadsheets are not movable parts. Objects nested inside a Part or Body container are not supported. Cut length editing is for rectangular `Part::Box` objects; other solids can move and rotate. Face alignment centres faces and can leave overlapping geometry. It does not create permanent assembly constraints.

## Recover after an update

Run `python3 install.py` again from this repository. The original standalone source copies in the parent DIY folder are also preserved. Keep custom tools in this add-on rather than editing Woodworking's `InitGui.py`.

## Checks

`python3 -m unittest discover -s tests` checks startup integration with simulated FreeCAD interfaces. Geometry and Qt controls can also be tested with FreeCAD's bundled Python as described in the test files. Rendering in the user's live OpenGL view requires a manual check.

## Dimension sources

- [Builder Depot 4×2 PAR](https://www.builderdepot.co.uk/50mm-x-100mm-planed-softwood-par-timber-4in-x-2in)
- [Builder Depot 3×2 PAR](https://www.builderdepot.co.uk/50mm-x-75mm-planed-softwood-par-timber-3in-x-2in)
- [Builder Depot 3×4 PAR](https://www.builderdepot.co.uk/75mm-x-100mm-planed-softwood-par-timber-4in-x-3in)

## Addon Manager package

`package.xml` describes this independent workbench. The repository is private and is not in the public Addon Manager list. Public distribution would need a license choice, maintainer contact, and listing review. The installer works now without that listing.
