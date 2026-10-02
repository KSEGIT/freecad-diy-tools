# Stable Auto Move grip and target intent

User reports physical mouse motion remains jumpy and nearby solids steal joints. Preserve the original Move command and independent add-on. Existing source feature probes span a long beam, allowing unrelated objects under remote ends to become depth candidates; exact-key retention only extends capture by two pixels.

Preserve selected native pickup, recognise nearby starting edge/corner while retaining the mouse-to-grip offset. Direct cursor Face/Edge/Vertex intent selects the target and adjacent planar contact faces; all other solids remain collision blockers. If the pointer is not over a target, retain the existing contact within a bounded release range or use only local source probes near the pointer. Middle pickup favours nearby upper/lower side edges instead of distant ends. Allow deliberate target changes and release when moving away; preserve angle, axis locks, Cancel and Undo.

Engine and UI implemented separately with regression tests. Fresh combined review and checks precede independent installation and feature PR update. User supplied snap test document is used read-only; original file hash must remain unchanged. Live physical mouse dispatch is unverified while computer use and local RPC are unavailable.

## Verified result

Fresh combined review approved bf50a3b, b21caab and 957c824. Native checkout checks: connection 25 passed, movement 40 passed, geometry helpers 7 passed, toolbar 9 passed, startup/package/install 8 passed. Original Move/Rotate, editor and geometry checks passed; compileall and git diff --check passed.

Used a temporary copy of the supplied snap test through FreeCAD MCP. Native Qt mouse events dispatched into the real viewer reached Coin at correct Retina pixel scaling. Five pointer changes over lower rail Edge10 retained the same contact key and exact translation (-44, -3.148622124993267, -1456) mm. Contact had zero gap and zero overlap; placement and Undo restored the original temporary-model placement. Repeated same-pixel face motion differed below 0.0003 mm, with tiny camera float drift. The source FCStd SHA-256 remained unchanged. Physical human mouse feel remains a manual check.
