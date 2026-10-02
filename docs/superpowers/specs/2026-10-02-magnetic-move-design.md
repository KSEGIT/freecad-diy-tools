# Magnetic Move

Approved scope A: magnetic cursor placement and measurements first. Add a distinct universal toolbar/Edit command; preserve normal Move and all Woodworking files. No new dependency.

Select one independent solid, activate Magnetic Move, click a source corner, move cursor with a translucent solid preview, click to commit exact translation. Snap to visible independent solids' real corners, straight-edge midpoints, and planar face points. Show a clear target marker, destination label, XYZ delta, travel distance and guides. Snap tolerance is in screen pixels, independent of zoom. A face snap uses the picked surface point (never forces centre or rotation). Corners outrank midpoints and faces within tolerance.

Movement defaults to a camera-facing plane through the chosen anchor; snapped targets use true world coordinates. X/Y/Z lock restricts movement to a world axis through the anchor and rejects targets that violate it. Provide keyboard X/Y/Z, Escape cancellation, and an editable exact distance along a locked axis. Shift temporary magnet bypass is optional only if reliable. Do not change angle during movement.

Preview uses only temporary unpickable Coin nodes; do not mutate the model until placement. One commit equals one Undo transaction. Cancel, switching document/view/workbench, object removal or errors must remove callbacks and guides and restore appearance without model changes. Reject nested Part/Body objects as existing tools do. Hide current source selection to avoid confusing highlight, but do not change source visibility. Exclude source and hidden objects from targets.

This is placement, not a persistent assembly constraint. Grouped frames, copies, cut handles and rotation snapping belong to later scope.
