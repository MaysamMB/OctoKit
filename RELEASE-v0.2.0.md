# OctoKit v0.2.0

- Add Storage Explorer: read-only drive overview, hierarchical logical sizes,
  guided largest-child summaries, top 100 files, cancellation and item re-scan.
- Rename the application title, sidebar and About page to OctoKit.
- Add an OctoKit.spec build producing dist/OctoKit/OctoKit.exe.
- Preserve the existing WinToolkit settings/templates directories for upgrades.

Windows 10/11 x64: download OctoKit-v0.2.0-win64.zip, extract the complete folder,
then launch OctoKit.exe. Keep the _internal folder beside it. Python is not
required for the packaged build. The executable is unsigned.

Storage Explorer never deletes files. Logical sizes are not physical/reclaimable
space. Linked/cloud/inaccessible entries are excluded and marked partial.
Hard links may be counted more than once. Name-based advice is not a guarantee
that an item is safe to remove. Scans stop at 300,000 nodes with partial results.

Source testing: full Linux suite passed; Windows source trial reported working
by the maintainer. A newly built Windows executable must be smoke-tested before
publishing the release. Do not attach an older executable to the new release.
