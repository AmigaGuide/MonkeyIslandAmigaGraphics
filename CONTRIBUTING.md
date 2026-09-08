# Contributing

Contributions to MonkeyIslandAmigaGraphics are welcome.

The project currently targets the original, unmodified Amiga release of
*The Secret of Monkey Island*. Changes should preserve compatibility with
the four original `disk01.lec` to `disk04.lec` resource files.

## Reporting Problems

When reporting an extraction problem, please include:

- The affected disk, room and resource where known.
- Relevant diagnostic output from the program.
- A description of the expected and actual result.
- Whether the game data is from the original unmodified Amiga release
  or a modified/cracked version.

Please do not attach or submit copyrighted original game data.

## Code Contributions

Pull requests are welcome.

Where practical:

- Keep changes focused and clearly described.
- Preserve the existing diagnostic output where it remains useful.
- Avoid unnecessary changes to working decoding logic.
- Test changes against all four game disks.
- Confirm that existing room, object and costume extraction continues
  to work correctly.

New decoding work should document the relevant SCUMM resource structure
or other technical basis used to implement it.

## Licensing

By contributing code to this repository, you agree that your contribution
may be distributed under the project's GNU General Public License
version 3 or later (GPLv3+).
