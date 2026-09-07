# MonkeyIslandAmigaGraphics

**MonkeyIslandAmigaGraphics** is a Python project for parsing and extracting graphical resources from the Amiga version of *The Secret of Monkey Island*.

The project was created primarily to extract the original room background artwork directly from the Amiga game resources, without objects or other graphical elements being composited over the backgrounds.

## Project Status

### Version 1.1.0

Version 1.1.0 successfully extracts both the main `BM` room backgrounds and `OI` object images from all four disks of the Amiga version of *The Secret of Monkey Island*.

The program:

* Parses the SCUMM resource structure contained within the Amiga `.lec` files.
* Locates room (`RO`) resources and their associated headers, palettes, `BM` bitmap data and `OI` object images.
* Reads the bitmap strip-offset tables used by room and object graphics.
* Decodes the `BMCOMP_PIX32` compression used by the Amiga version of the game.
* Reconstructs individual 8-pixel-wide strips into complete graphical resources.
* Applies the appropriate 16-colour Amiga room palette.
* Saves extracted graphics as 16-colour indexed PNG images.
* Creates palette reference images for each room.

The current implementation has successfully extracted:

* **85 room background images**
* **659 object images**

across the four game disks, with no obvious graphical corruption observed during testing.

Room backgrounds are deliberately exported without object images composited over them, preserving the clean background artwork as stored in the game resources.

Development will continue with the aim of identifying and extracting additional graphical resources from the game.

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

Development and testing has been performed using resource files from the **original, unmodified Amiga release** of *The Secret of Monkey Island*.

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

Object images are written to:

```text
Objects/
├── disk01/
│   ├── room_01/
│   ├── room_02/
│   └── ...
├── disk02/
├── disk03/
└── disk04/
```

Each object image retains the object identifier stored in its OI resource, for example:

```text
Objects/disk01/room_01/object_113.png
```

The generated `Rooms/`, `Palettes/` and `Objects/` directories are excluded from Git.


## Graphics Format

The Amiga room backgrounds and object images are stored as compressed 8-pixel-wide bitmap strips.

For the resources currently supported by this project, each strip uses compression method `0x0A`, corresponding to the `BMCOMP_PIX32` decoding path used by ScummVM for the Amiga version of *The Secret of Monkey Island*.

The same strip decoder is used successfully for both main `BM` room backgrounds and `OI` object images.

For room backgrounds, the image dimensions are obtained from the room metadata. Object image widths are derived from their strip-offset tables, while their heights are determined by finding the height for which every compressed strip decodes completely and consumes its full payload.

The decoder produces 4-bit colour values representing 16 colours. These correspond to entries 16–31 of the room's 32-entry palette.

Extracted graphics are therefore saved as **16-colour indexed PNG files**, preserving the indexed-colour nature of the original Amiga artwork rather than converting the images to 24-bit RGB.


## Goals

Version 1.0.0 fulfilled the project's original objective of extracting the clean room background artwork.

Version 1.1.0 extends the extractor to `OI` object images while continuing to preserve room backgrounds as separate, unpopulated images.

Future development will investigate other graphical resources contained within the game with the longer-term aim of extracting as much of the original Amiga artwork as practical.


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
