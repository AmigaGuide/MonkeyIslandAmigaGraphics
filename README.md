# MonkeyIslandAmigaGraphics

**MonkeyIslandAmigaGraphics** is a Python project for parsing and extracting graphical resources from the Amiga version of *The Secret of Monkey Island*.

The project was created primarily to extract the original room background artwork directly from the Amiga game resources, without objects or other graphical elements being composited over the backgrounds.

## Project Status

### Version 1.0.0

Version 1.0.0 successfully extracts the main `BM` room backgrounds from all four disks of the Amiga version of *The Secret of Monkey Island*.

The program:

* Parses the SCUMM resource structure contained within the Amiga `.lec` files.
* Locates room (`RO`) resources and their associated headers, palettes and `BM` bitmap data.
* Reads the bitmap strip-offset table.
* Decodes the `BMCOMP_PIX32` compression used by the Amiga version of the game.
* Reconstructs the individual 8-pixel-wide strips into complete room backgrounds.
* Applies the appropriate 16-colour Amiga room palette.
* Saves the extracted backgrounds as 16-colour indexed PNG images.
* Creates palette reference images for each room.

The current implementation has successfully extracted **85 room background images** across the four game disks.

Development will continue with the aim of extracting additional graphical resources while retaining the room backgrounds as separate, unpopulated images.

## Requirements

Python 3 and the Pillow imaging library are required.

Pillow can be installed with:

```bash
pip install Pillow
```

A legally obtained copy of the Amiga version of *The Secret of Monkey Island* is also required.

### Game Files

The following four resource files are required:

```text
disk01.lec
disk02.lec
disk03.lec
disk04.lec
```

These should be placed inside a directory named `resource` in the project root:

```text
MonkeyIslandAmigaGraphics/
├── mi_amiga_graphics.py
├── resource/
│   ├── disk01.lec
│   ├── disk02.lec
│   ├── disk03.lec
│   └── disk04.lec
└── ...
```

The `resource/` directory is excluded from Git and no original game data is distributed with this project.

Development and testing of version 1.0.0 has been performed using resource files from the **original, unmodified Amiga release** of *The Secret of Monkey Island*.

Modified or cracked/hacked versions of the game have not currently been tested and may contain differences that affect parsing or extraction. Use of the original, unmodified game data is therefore recommended.

## Usage

With the four `.lec` files in the `resource/` directory, run:

```bash
python mi_amiga_graphics.py
```

The program processes all four disks.

Room backgrounds are written to:

```text
Rooms/
├── disk01/
├── disk02/
├── disk03/
└── disk04/
```

Palette reference images are written to:

```text
Palettes/
├── disk01/
├── disk02/
├── disk03/
└── disk04/
```

Generated output directories are excluded from Git.

## Graphics Format

The Amiga room backgrounds are stored as compressed 8-pixel-wide bitmap strips.

For the resources currently supported by this project, each strip uses compression method `0x0A`, corresponding to the `BMCOMP_PIX32` decoding path used by ScummVM for the Amiga version of *The Secret of Monkey Island*.

The decoder produces 4-bit colour values representing 16 colours. These correspond to entries 16–31 of the room's 32-entry palette.

The extracted backgrounds are therefore saved as **16-colour indexed PNG files**, preserving the indexed-colour nature of the original artwork rather than converting the images to 24-bit RGB.

## Goals

Version 1.0.0 fulfils the project's original objective of extracting the clean room background artwork.

Future development may extend the extractor to other graphical resources contained within the game, including object images and other artwork.

These resources will be extracted separately rather than composited onto the room backgrounds.

## ScummVM

The [ScummVM](https://www.scummvm.org/) source code has been used as an important reference for understanding how the original SCUMM graphics data is decoded.

The `BMCOMP_PIX32` strip decoder in this project is a Python adaptation of the relevant decoding behaviour in ScummVM's SCUMM engine, including its `drawStripEGA()` implementation.

ScummVM is copyright its respective authors and is distributed under the GNU General Public License.

## Game Data and Copyright

Original game files and extracted game artwork are **not included** with this project.

Users must provide their own legally obtained copy of the relevant game data.

*The Secret of Monkey Island* and its original artwork are the property of their respective copyright holders.

## Licence

This project is distributed under the terms of the **GNU General Public License version 3 or later (GPLv3+)**.

See the `LICENSE` file for details.

## Acknowledgements

* The ScummVM project and its contributors for their extensive work documenting and implementing support for the SCUMM engine.
* Lucasfilm Games / LucasArts for *The Secret of Monkey Island*.
