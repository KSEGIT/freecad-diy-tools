# Publication status and checklist

Status checked on **2026-10-13** for publication candidate **0.6.2**. Public release is pending license, maintainer contact and visibility decisions. The add-on is not listed in the public FreeCAD Addon Manager. Preparing a release branch, tag or ZIP does not establish an Index listing.

## Decisions required before public distribution

- [ ] Confirm the license and the rights to distribute all code, icons and other resources. The current metadata declares `UNLICENSED`; there is no chosen public distribution license. Add the license text and keep its SPDX identifier consistent in `package.xml` and applicable file headers.
- [ ] Choose a public maintainer email and add it to `package.xml`. Do not infer permission to publish an address from Git commit authorship.
- [ ] Confirm the intended repository visibility before making a private repository public.

## FreeCAD Addon Index blockers

The current [Index quality requirements](https://freecad.github.io/Addon-Academy/Topics/Addon-Index/Index/Qualities.html) require at least 30 days of repository and codebase history. The repository was created on **2026-10-01 at 21:36 UTC**. Its earliest repository age eligibility is **2026-10-31 at 21:36 UTC**; confirm the full codebase also meets the age requirement before submitting.

The same requirements and the [manifest reference](https://freecad.github.io/Addon-Academy/Topics/Structuring/Manifest/) need these checks:

- [ ] Resolve the missing license and maintainer contact above.
- [ ] Resolve the global toolbar and menu design: current Index rules require UI effects to stay in the add-on's own workbench. DIY tools intentionally remain visible across workbenches.
- [ ] Resolve startup `sys.path` changes in `DIYWorkbenchTools/InitGui.py`; the Index rules disallow them even in the legacy layout.
- [ ] Review the intentional workbench-content loader workaround. The current manifest names a workbench content item but supplies no `<classname>` and registers no selectable workbench. Do not add a fictitious class just to satisfy metadata checks. Agree a compliant content/load design with the FreeCAD maintainers or implement and test a real workbench design.
- [ ] Test the resulting package on the latest supported FreeCAD, including startup, workbench changes, saved toolbar visibility, mouse placement, snapping, cancel and Undo. The current target is FreeCAD 1.1+; verification has used macOS FreeCAD 1.1.3. Windows and Linux are untested.
- [ ] Review the remaining Index requirements, including Qt wrappers, startup side effects, user data handling and security reports.

## Release preparation

- [ ] Preserve a backup of the installed add-on and any uncommitted source changes. Reconcile them in an isolated branch; never replace local customizations without a backup.
- [ ] Review the branch diff and run the applicable unit, FreeCAD geometry and Qt checks listed in the README. Record any manual checks that remain incomplete.
- [ ] Confirm `package.xml`, changelog and tag agree on **0.6.2**, and set the metadata release date to **2026-10-13** when that version is published.
- [ ] Push the reviewed branch and open a pull request. Do not push directly to the default branch.
- [ ] Before merging or publishing from a stable branch, change the `package.xml` repository `branch` and README URL to that stable branch or release tag. They currently point to the preparation branch `codex/publish-diy-tools`; do not delete that remote branch while its manifest is used.
- [ ] After approval and integration, tag the reviewed release commit as `v0.6.2` and publish release notes and a ZIP. If releasing a reviewed branch before integration, state that branch and commit clearly.
- [ ] Keep the ZIP's `DIYWorkbenchTools/` directory intact. Include `package.xml`, README, changelog and the chosen license at the archive root. Manual users copy only `DIYWorkbenchTools` into their user data `Mod` directory.
- [ ] Test extraction and installation in a temporary `Mod` directory before attaching the ZIP. Confirm `DIYWorkbenchTools/InitGui.py` exists after installation.

## Custom repository source

After license and visibility approval, publish the reviewed repository and share its URL through the [official Reference channel](https://freecad.github.io/Addon-Academy/Guides/Publishing/Reference/). This route supports Addon Manager updates without an Index listing. Confirm that users select the released branch or tag; until the pull request is integrated, `main` remains at 0.6.1. Verify custom-source installation in a separate profile before claiming it is tested.

## Index submission after blockers are resolved

- [ ] Recheck the current Index submission instructions and repository age.
- [ ] Choose a stable tracked release branch. Keep the repository URL's `branch` attribute consistent with the branch containing the manifest; increment version and date for each published change.
- [ ] Open an **Addon – Addition** issue at [FreeCAD/Addons](https://github.com/FreeCAD/Addons/issues/new/choose), including the public repository URL and release details. See the [Indexed publishing guide](https://freecad.github.io/Addon-Academy/Guides/Publishing/Indexed/). Record the issue URL here. Index maintainers decide acceptance.
- [ ] Verify installation and updates through Addon Manager after the listing is accepted.

Until these steps are complete, describe distribution accurately as a repository or GitHub release with manual installation, not an official Addon Manager listing.
