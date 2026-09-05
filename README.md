# MonkeyIslandAmigaGraphics

**MonkeyIslandAmigaGraphics** is an experimental Python project for parsing and extracting graphical resources from the Amiga version of *The Secret of Monkey Island*.

The primary goal is to understand and decode the main `BM` graphics used for the game's rooms and export them into a modern image format.

## Project Status

This project is currently a **work in progress**.

It originated from an earlier Python experiment named `SCUMM_Parser.py`, which successfully progressed through the structure of the game resources far enough to identify and extract information including:

* Room resources
* Room dimensions
* Palette data
* `BM` bitmap resources

The remaining challenge is to correctly decode the compressed bitmap data and reconstruct the room graphics.

The current implementation is being developed from that earlier work with a deliberately narrower objective: successfully decode the main room backgrounds before attempting to reproduce any unnecessary parts of the SCUMM engine.

## Goals

The primary objective is to:

1. Parse the relevant SCUMM resources from the Amiga game data.
2. Locate the main `BM` resource for each room.
3. Decode the compressed bitmap data.
4. Reconstruct the indexed-colour room image using its appropriate palette.
5. Export the decoded graphics to a standard image format.

Where additional graphical resources are encountered while parsing a room, these may also be decoded and exported where practical. The main room `BM`, however, remains the focus of the project.

## ScummVM

The [ScummVM](https://www.scummvm.org/) source code has been used as an important reference for understanding how the original SCUMM graphics data is decoded.

Some graphics decoding routines in this project may be Python adaptations or translations of routines from the ScummVM SCUMM engine. Such code will be identified and attributed where appropriate.

ScummVM is copyright its respective authors and is distributed under the GNU General Public License.

## Game Data

Original game files are **not included** with this project.

The `resource/` directory used during development contains locally supplied game data and is deliberately excluded from Git.

Users of this software must provide their own legally obtained copy of the relevant game data.

## Reference Code

The `reference/` directory contains the previous experimental version of the Python parser:

`SCUMM_Parser OLD.py`

This has been retained as a historical reference while development continues in:

`mi_amiga_graphics.py`

## Licence

This project is distributed under the terms of the **GNU General Public License version 3 or later (GPLv3+)**.

See the `LICENSE` file for details.

## Acknowledgements

* The ScummVM project and its contributors for their extensive work documenting and implementing support for the SCUMM engine.
* Lucasfilm Games / LucasArts for *The Secret of Monkey Island*.
