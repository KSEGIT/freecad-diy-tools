# Automatic magnetic Move — user correction

The user rejected the previous corner-picking Magnetic Move. Correct flow: select one part -> Auto Move -> cursor moves the whole part immediately -> logical connections snap automatically -> click once to place. No source corner/face selection. Join corners remains separate for explicit alignment. Ordinary grouped independent solids remain supported; original Woodworking is never modified.

A new Auto Move button starts this automatic flow; original Move part keeps native transform handles. The separate magnet button (legacy DIY_MagneticMove command) is a checkable Auto snap on/off toggle, default enabled, persisted in preferences and available during an active move. It does not start movement. S and the compact Snap checkbox toggle the same state. Rotate and Join corners remain separate. Native precision arrows remain available through existing Place & edit.

Use the part centre as automatic pickup reference. Cursor movement starts on a camera-facing plane through that centre; X/Y/Z locks support depth changes and exact signed distance entry. Show a ghost immediately at the original position, then cursor tracking without any initial corner click. Put compact modeless controls at the edge of the main window, not centred over the model. Show movement measurements and a labelled connection guide; Escape cancels, S toggles snapping. One final placement is one Undo step; preview never mutates the object.

Match whole-part geometry: parallel matching timber end faces should align end-to-end with width/thickness flush; opposing parallel faces should contact without overlap while allowing in-face movement; near corners can align automatically if the resulting solids do not overlap. Preserve angle. Do not guess or change rotation. Use a screen-pixel capture radius and finite world proximity, reject distant depth jumps and source/hidden/nested targets. Keep a stable candidate near tolerance boundaries. If no sensible joint is near, remain free-moving. Automatic placement is not a persistent assembly constraint.

Acceptance: two 1700x94x44 boxes connect lengthwise at their ends; a horizontal rail butts against an upright side; side-by-side or stacked faces meet without embedding; wrong-overlapping corner matches are rejected; moving away releases snap; axis locks are obeyed; rotated matching boxes work; Auto Move enters this flow with no corner-picking prompt; all cancel/lifecycle/Undo checks remain valid.

Research checked Draft/BIM, Woodworking magicMove/panelMove2Face/panelMove2Anchor and Std Transform; their point snapping, axis steps or explicit alignment do not infer this whole-timber connection flow. Primary patterns used: SketchUp https://help.sketchup.com/en/sketchup/moving-entities-around (grips/inference/axis/measurements) and Autodesk Forge/APS https://aps.autodesk.com/blog/drag-and-drop-snap-points (all moving-to-placed connector screen matching). Here connectors are generated from timber geometry; no imported service or dependency is needed.

## User correction

Keep DIY_MovePart and its native 3D transform handles unchanged. Add a distinct DIY_AutoMove toolbar/Edit action for immediate cursor movement. Auto snap remains a separate saved toggle. The blue cursor with green contact icon distinguishes Auto Move from the original blue arrows.
