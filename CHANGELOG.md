# Changelog

## 0.6.2 — 2026-10-13

- Include the local frame-end snapping fix developed on 2026-10-02: Auto Move can close nearby frame ends when a part is held from a middle grip, without jumping to a distant end. Add lifecycle checks for this behavior (`0065a95`, recovered into the publication branch).
- Add manual installation and update instructions for macOS, Linux and Windows, with a warning to back up local customizations.
- Document compatibility limits and the remaining FreeCAD Addon Index publication requirements.
- Add the MIT License and public maintainer contact; pin package metadata and installation guidance to release tag `v0.6.2`.

## 0.6.1 — 2026-10-02

- Prefer nearby joints with adjacent edges and planes flush (`7066411`).
- Add checks for the extra alignment near face boundaries.

## 0.6.0 — 2026-10-02

- Stabilize snapping using held and hovered timber features (`bf50a3b`).
- Preserve the pickup point and keep snapping on the intended destination (`b21caab`).
- Recognize corner grips and preserve pickup offset under axis locks (`957c824`).
- Record the stable grip and target-aware snapping release (`a18af63`).

## 0.5.1 — 2026-10-02

- Resolve automatic contacts at visible face depth and correct pickup behavior (`6fa3548`, `68b1b9a`).
- Retain collision blockers when retrying a rejected contact (`136f939`).
- Align nearby parallel edges without jumping to distant rail ends (`deac28b`).
- Document snap-depth verification and the release repair (`7b621f8`).

## Earlier development — 2026-10-01 to 2026-10-02

- Restore DIY tools as an independent add-on, then expose them in a universal toolbar with saved visibility.
- Add whole-part automatic movement, contact inference, preview lifecycle checks and a persistent snap toggle.
- Keep native Move handles and provide a separate Auto Move command.

Entries describe verified Git history; they do not imply that a public release or Addon Manager listing existed at that time.
