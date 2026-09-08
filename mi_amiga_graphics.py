import os
from PIL import Image, ImageDraw, ImageFont

ROOMS_OUTPUT_DIR    = "Rooms"
PALETTES_OUTPUT_DIR = "Palettes"
COSTUMES_OUTPUT_DIR = "Costumes"
OBJECTS_OUTPUT_DIR  = "Objects"

__version__ = "1.2.0"

CHUNK_LABELS = {
    'LE': 'LucasArts Entertainment Company File',
    'FO': 'File Offsets',
    'LF': 'LucasArts File Format',
    'RO': 'Room',
    'HD': 'Room Header',
    'CC': 'Colour Cycle',
    'SP': '?',
    'BX': 'Box Description and Matrix',
    'PA': 'Palette',
    'SA': '?',
    'BM': 'Bitmap',
    'OI': 'Object Image',
    'NL': 'Script?',
    'SL': 'Script?',
    'OC': 'Object Code?',
    'EX': 'Exit Code?',
    'EN': 'Entry Code?',
    'LC': '?',
    'LS': 'Local Script',
    'SC': 'Script',
    'AM': 'Some Amiga Specific Block',
    'CO': 'Costume?'
}


def create_costume_stats():
    """
    Create counters used to summarise costume extraction.

    Returns:
        A dictionary containing costume extraction counters and
        recorded problem details.
    """

    return {
        "costumes_processed": 0,
        "cel_candidates": 0,
        "cels_saved": 0,
        "zero_size": 0,
        "implausible_size": 0,
        "decode_failures": 0,
        "save_failures": 0,
        "unsupported_formats": 0,
        "problems": []
    }


def print_costume_summary(costume_stats):
    """
    Print a summary of costume extraction results.

    Args:
        costume_stats: Statistics dictionary populated while
            processing CO costume resources.
    """

    problems = costume_stats["problems"]

    problem_costumes = {
        (
            problem["disk"],
            problem["room"],
            problem["costume"]
        )
        for problem in problems
    }

    print()
    print("=" * 70)
    print("COSTUME EXTRACTION SUMMARY")
    print("=" * 70)

    print(
        f"CO resources processed:          "
        f"{costume_stats['costumes_processed']}"
    )

    print(
        f"Unique cel candidates found:     "
        f"{costume_stats['cel_candidates']}"
    )

    print(
        f"Costume cels saved:              "
        f"{costume_stats['cels_saved']}"
    )

    print()
    print(
        f"Skipped zero-size cels:          "
        f"{costume_stats['zero_size']}"
    )

    print(
        f"Skipped implausible dimensions: "
        f"{costume_stats['implausible_size']}"
    )

    print(
        f"Cel decode failures:             "
        f"{costume_stats['decode_failures']}"
    )

    print(
        f"Costume cel save failures:       "
        f"{costume_stats['save_failures']}"
    )

    print(
        f"Unsupported costume formats:     "
        f"{costume_stats['unsupported_formats']}"
    )

    print(
        f"Costumes with problems:          "
        f"{len(problem_costumes)}"
    )

    if problems:
        print()
        print("Problem details:")

        max_problem_lines = 50

        for problem in problems[:max_problem_lines]:

            location = (
                f"disk{problem['disk']:02} / "
                f"room_{problem['room']:02} / "
                f"costume_{problem['costume']:02}"
            )

            if problem["cel"] is not None:
                location += (
                    f" / cel_{problem['cel']:03}"
                )

            print(
                f"  {location}: "
                f"{problem['message']}"
            )

        if len(problems) > max_problem_lines:
            print(
                f"  ... plus "
                f"{len(problems) - max_problem_lines} "
                f"additional problems."
            )

    else:
        print()
        print("No costume extraction problems recorded.")

    print("=" * 70)


def read_signed_le16(data, offset):
    """
    Read a signed 16-bit little-endian integer.

    Args:
        data: Byte sequence containing the value.
        offset: Offset of the two-byte value within data.

    Returns:
        The decoded signed integer.
    """
    value = int.from_bytes(
        data[offset:offset + 2],
        "little"
    )

    if value >= 0x8000:
        value -= 0x10000

    return value


def parse_lec_header_and_fo(
    filepath,
    disk_number,
    costume_stats
):
    """
    Parse an encrypted Amiga SCUMM LEC resource file.

    Decrypts the file using the SCUMM XOR key 0x69, validates the
    top-level LE chunk, reads the FO file-offset table, and passes
    each embedded LF resource to parse_lf().

    Args:
        filepath: Path to the diskXX.lec resource file.
        disk_number: Source disk number, used when organising output.
        costume_stats: Statistics dictionary updated during costume
            extraction.
    """
    with open(filepath, 'rb') as f:
        raw_data = f.read()

    # Apply XOR decryption with 0x69
    data = bytes(b ^ 0x69 for b in raw_data)
    pointer = 0

    # Parse LE section
    file_size = int.from_bytes(data[pointer:pointer+4], 'little')
    chunk_id = data[pointer+4:pointer+6].decode('ascii', errors='ignore')
    print(f"Declared file size: {file_size} bytes")

    if chunk_id != 'LE':
        print("Invalid LE header.")
        return
    else:
        print("Found LE section.")

    pointer += 6

    # Parse FO section
    fo_chunk_size = int.from_bytes(data[pointer:pointer+4], 'little')
    pointer += 4

    fo_id = data[pointer:pointer+2].decode('ascii', errors='ignore')
    if fo_id != 'FO':
        print("Missing FO section.")
        return
    else:
        print(f"Found FO section (declared size: {fo_chunk_size} bytes)")

    pointer += 2
    fo_payload_size = fo_chunk_size - 6
    fo_data = data[pointer:pointer + fo_payload_size]
    pointer += fo_payload_size

    file_count = fo_data[0]
    print(f"\nEmbedded file count: {file_count}")
    print()

    for i in range(file_count):
        entry_offset = 1 + i * 5
        fo_id_byte = fo_data[entry_offset]
        file_pointer = int.from_bytes(fo_data[entry_offset + 1 : entry_offset + 5], 'little')
        print(f"File {i + 1}: Offset {file_pointer}")

        lf_size = int.from_bytes(data[file_pointer:file_pointer + 4], 'little')
        lf_data = data[file_pointer : file_pointer + lf_size]

        parse_lf(
            lf_data,
            i + 1,
            fo_id_byte,
            disk_number,
            costume_stats
        )


def parse_lf(
    lf_data,
    file_index,
    fo_id_byte,
    disk_number,
    costume_stats
):
    """
    Parse an LF resource block from a SCUMM LEC file.

    Validates the LF header and its ID against the corresponding FO
    entry, enumerates the chunks contained within the LF block, and
    passes the RO room resource to parse_ro(), then processes any
    LF-level CO costume resources using the room palette.

    Args:
        lf_data: Complete LF block, including its chunk header.
        file_index: Sequential index of the embedded file on this disk.
        fo_id_byte: Resource ID obtained from the FO table.
        disk_number: Source disk number.
        costume_stats: Statistics dictionary updated during costume
            extraction.
    """
    print(f"\nFile {file_index}")
    declared_size = int.from_bytes(lf_data[0:4], 'little')
    lf_id = lf_data[4:6].decode('ascii', errors='ignore')
    actual_id_byte = lf_data[6]

    print(f"  Declared LF block size: {declared_size} bytes")
    print(f"  Header found: '{lf_id}'")

    if lf_id != 'LF':
        print("  Invalid LF header. Skipping block.")
        return

    if actual_id_byte == fo_id_byte:
        print(f"  LF ID byte matches FO entry: {actual_id_byte:02X}")
    else:
        print(f"  Warning: LF ID byte {actual_id_byte:02X} does not match FO entry {fo_id_byte:02X}")

    pointer = 8
    contents = []

    print("  Contained chunks:")
    while pointer + 6 <= len(lf_data):
        chunk_size = int.from_bytes(lf_data[pointer:pointer + 4], 'little')
        chunk_id = lf_data[pointer + 4:pointer + 6].decode('ascii', errors='ignore')
        label = CHUNK_LABELS.get(chunk_id, '?')

        print(f"    Offset {pointer:>5}: ID='{chunk_id}', Label='{label}', Size={chunk_size} bytes")
        contents.append((pointer, chunk_id, chunk_size))
        pointer += chunk_size

        if pointer == len(lf_data):
            print("  End of LF block reached cleanly.")
            break
        elif pointer > len(lf_data):
            print("  Warning: last chunk extends beyond LF block.")
            break

    room_palette = None

    # Process the room first so that its palette is available
    # to associated costume resources.
    for offset, chunk_id, chunk_size in contents:
        if chunk_id == 'RO':
            ro_data = lf_data[
                offset:offset + chunk_size
            ]

            room_palette = parse_ro(
                ro_data,
                file_index,
                disk_number
            )

    # Costumes are LF-level resources associated with this room.
    costume_number = 0

    for offset, chunk_id, chunk_size in contents:
        if chunk_id == 'CO':

            costume_number += 1

            if room_palette is None:
                print(
                    "  Cannot decode CO: room palette "
                    "is unavailable."
                )
                continue

            co_data = lf_data[
                offset:offset + chunk_size
            ]

            parse_co(
                co_data,
                room_palette,
                disk_number,
                file_index,
                costume_number,
                costume_stats
            )


def parse_ro(
    ro_data,
    file_index,
    disk_number
):
    """
    Parse an RO room resource and locate its graphical components.

    Enumerates the room subchunks, obtains room dimensions from HD,
    the palette from PA, the main background from BM, and object
    graphics from OI. The room palette is returned so LF-level
    costume resources can use it during decoding.

    Args:
        ro_data: Complete RO block, including its chunk header.
        file_index: Sequential index of the embedded file on this disk.
        disk_number: Source disk number.

    Returns:
        The room palette as a list of RGB tuples, or None if no usable
        palette was found.
    """
    if len(ro_data) < 6:
        print("  RO data too short to be valid.")
        return

    declared_size = int.from_bytes(ro_data[0:4], 'little')
    ro_id = ro_data[4:6].decode('ascii', errors='ignore')

    print("\n  >>> parse_ro() called")
    print(f"  RO declared size: {declared_size} bytes")
    print(f"  Header found: '{ro_id}'")

    if ro_id != 'RO':
        print("  Invalid RO header. Expected 'RO'.")
        return

    pointer = 6
    contents = []
    chunk_counts = {}

    print("  Contained subchunks in RO:")
    while pointer + 6 <= len(ro_data):
        chunk_size = int.from_bytes(
            ro_data[pointer:pointer + 4],
            'little'
        )

        chunk_id = ro_data[
            pointer + 4:pointer + 6
        ].decode('ascii', errors='ignore')

        label = CHUNK_LABELS.get(chunk_id, '?')

        print(
            f"    Offset {pointer:>5}: "
            f"ID='{chunk_id}', "
            f"Label='{label}', "
            f"Size={chunk_size} bytes"
        )

        contents.append(
            (pointer, chunk_id, chunk_size)
        )

        chunk_counts[chunk_id] = (
            chunk_counts.get(chunk_id, 0) + 1
        )

        pointer += chunk_size

        if pointer == len(ro_data):
            print("  End of RO block reached cleanly.")
            break

        elif pointer > len(ro_data):
            print(
                "  Warning: last subchunk extends "
                "beyond RO block."
            )
            break

    print("  Subchunk counts:")
    for chunk_id, count in chunk_counts.items():
        label = CHUNK_LABELS.get(chunk_id, '?')
        print(
            f"    {chunk_id}: {count} ({label})"
        )

    if chunk_counts.get('BM', 0) == 0:
        print(
            "  No BM chunk found — skipping "
            "detailed parsing."
        )
        return

    # Room values required by the graphics decoders.
    width = None
    height = None
    palette_rgb = None

    for offset, chunk_id, chunk_size in contents:

        if chunk_id == 'HD':
            hd_data = ro_data[
                offset:offset + chunk_size
            ]

            width, height = parse_hd(hd_data)

        elif chunk_id == 'PA':
            pa_data = ro_data[
                offset:offset + chunk_size
            ]

            palette_rgb = parse_pa(
                pa_data,
                file_index,
                disk_number
            )

        elif chunk_id == 'BM':
            bm_data = ro_data[
                offset:offset + chunk_size
            ]

            if width is None or height is None:
                print(
                    "  Cannot decode BM: room dimensions "
                    "are unavailable."
                )
                continue

            if palette_rgb is None:
                print(
                    "  Cannot decode BM: room palette "
                    "is unavailable."
                )
                continue

            parse_bm(
                bm_data,
                file_index,
                width,
                height,
                palette_rgb,
                disk_number
            )

        elif chunk_id == 'OI':
            oi_data = ro_data[
                offset:offset + chunk_size
            ]

            if palette_rgb is None:
                print(
                    "  Cannot decode OI: room palette "
                    "is unavailable."
                )
                continue

            parse_oi(
                oi_data,
                file_index,
                palette_rgb,
                disk_number
            )

    return palette_rgb


def parse_hd(hd_data):
    """
    Parse an HD room-header chunk.

    Extracts the room dimensions and reports the number of objects
    associated with the room.

    Args:
        hd_data: Complete HD chunk, including its chunk header.

    Returns:
        A tuple containing the room width and height in pixels.
    """
    print("\n    >>> parse_hd() called")
    if len(hd_data) < 12:
        print("    HD chunk too short.")
        return

    width = int.from_bytes(hd_data[6:8], 'little')
    height = int.from_bytes(hd_data[8:10], 'little')
    num_objects = hd_data[10]

    print(f"    Room dimensions: {width} x {height}")
    print(f"    Number of objects: {num_objects}")

    return width, height


def parse_pa(pa_data, room_index, disk_number):
    """
    Parse a PA palette chunk and save a visual palette reference.

    Extracts the RGB colour entries from the room palette and creates
    a palette swatch PNG in the output directory for the source disk.

    Args:
        pa_data: Complete PA chunk, including its chunk header.
        room_index: Sequential index of the room within the source disk.
        disk_number: Source disk number.

    Returns:
        A list of (red, green, blue) tuples representing the palette,
        or None if the palette data is invalid.
    """
    print("\n    >>> parse_pa() called")

    if len(pa_data) < 8:
        print("    PA chunk too short.")
        return

    declared_size = int.from_bytes(pa_data[0:4], 'little')
    pa_id = pa_data[4:6].decode('ascii', errors='ignore')

    if pa_id != 'PA':
        print(f"    Invalid PA header: found '{pa_id}'")
        return

    colour_data_bytes = pa_data[6]
    colour_count = colour_data_bytes // 3
    separator = pa_data[7]

    if separator != 0x00:
        print(f"    Warning: unexpected non-zero separator byte: {separator:02X}")

    print(f"    Declared size: {declared_size} bytes")
    print(f"    Colour data bytes: {colour_data_bytes}")
    print(f"    Colour count: {colour_count}")

    expected_data_len = colour_count * 3
    start = 8
    end = start + expected_data_len

    if len(pa_data) < end:
        print(f"    Warning: not enough data for {colour_count} colours.")
        return

    print("    RGB values:")
    colours = []
    for i in range(colour_count):
        r, g, b = pa_data[start + i*3], pa_data[start + i*3 + 1], pa_data[start + i*3 + 2]
        colours.append((r, g, b))
        print(f"      {i:02}: R={r:02X}({r}) G={g:02X}({g}) B={b:02X}({b})")

    # Create image
    output_dir = os.path.join(
        PALETTES_OUTPUT_DIR,
        f"disk{disk_number:02}"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    swatch_size = 50
    font_size = 10
    cols = 8
    rows = (colour_count + cols - 1) // cols
    img_width = cols * swatch_size
    img_height = rows * (swatch_size + font_size * 2)

    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()

    for idx, (r, g, b) in enumerate(colours):
        x = (idx % cols) * swatch_size
        y = (idx // cols) * (swatch_size + font_size * 2)
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=(r, g, b))
        hex_text = f"#{r:02X}{g:02X}{b:02X}"
        dec_text = f"{r},{g},{b}"
        draw.text((x + 2, y + swatch_size), hex_text, fill='black', font=font)
        draw.text((x + 2, y + swatch_size + font_size), dec_text, fill='black', font=font)

    filename = os.path.join(
        output_dir,
        f"palette_{room_index:02}.png"
    )

    img.save(filename)
    print(f"    Palette image saved as '{filename}'")

    return colours


def decode_strip_ega(strip_payload, height):
    """
    Decode one 8-pixel-wide BMCOMP_PIX32 bitmap strip.

    Implements the decoding behaviour of ScummVM's drawStripEGA()
    routine used by the Amiga version of The Secret of Monkey Island.
    The compressed stream supports solid-colour runs, copies from the
    previous column, alternating two-colour runs, and extended run
    lengths.

    Pixels are decoded vertically, one column at a time, across the
    eight columns that make up a SCUMM bitmap strip.

    Args:
        strip_payload: Compressed strip data after the compression byte.
        height: Height of the room bitmap in pixels.

    Returns:
        A tuple containing:
            - Eight columns of decoded 4-bit colour indices (0-15).
            - The number of compressed payload bytes consumed.

    Raises:
        ValueError: If the compressed data is malformed or ends before
            all eight columns have been decoded.
    """
    columns = [
        [0 for _ in range(height)]
        for _ in range(8)
    ]

    src = 0
    x = 0
    y = 0

    def write_pixel(colour):
        nonlocal x, y

        if x >= 8:
            raise ValueError(
                "Decoder attempted to write beyond "
                "the 8-pixel strip width."
            )

        columns[x][y] = colour

        y += 1

        if y >= height:
            y = 0
            x += 1

    while x < 8:

        if src >= len(strip_payload):
            raise ValueError(
                f"Strip data ended early at column {x}, row {y}."
            )

        colour = strip_payload[src]
        src += 1

        # ----------------------------------------------------------
        # 1xxxxxxx
        # ----------------------------------------------------------
        if colour & 0x80:

            run = colour & 0x3F

            # ------------------------------------------------------
            # 11xxxxxx
            #
            # Alternate between two colours.
            # ------------------------------------------------------
            if colour & 0x40:

                if src >= len(strip_payload):
                    raise ValueError(
                        "Missing alternating colour byte."
                    )

                colour_pair = strip_payload[src]
                src += 1

                if run == 0:

                    if src >= len(strip_payload):
                        raise ValueError(
                            "Missing extended alternating run length."
                        )

                    run = strip_payload[src]
                    src += 1

                high_colour = (colour_pair >> 4) & 0x0F
                low_colour = colour_pair & 0x0F

                for z in range(run):

                    if z & 1:
                        write_pixel(low_colour)
                    else:
                        write_pixel(high_colour)

            # ------------------------------------------------------
            # 10xxxxxx
            #
            # Copy from previous column.
            # ------------------------------------------------------
            else:

                if run == 0:

                    if src >= len(strip_payload):
                        raise ValueError(
                            "Missing extended copy run length."
                        )

                    run = strip_payload[src]
                    src += 1

                for _ in range(run):

                    if x == 0:
                        raise ValueError(
                            "Previous-column copy encountered "
                            "while decoding column 0."
                        )

                    colour_from_previous_column = columns[x - 1][y]

                    write_pixel(
                        colour_from_previous_column
                    )

        # ----------------------------------------------------------
        # 0xxxxxxx
        #
        # Solid colour run.
        # ----------------------------------------------------------
        else:

            run = colour >> 4

            if run == 0:

                if src >= len(strip_payload):
                    raise ValueError(
                        "Missing extended solid run length."
                    )

                run = strip_payload[src]
                src += 1

            solid_colour = colour & 0x0F

            for _ in range(run):
                write_pixel(solid_colour)

    return columns, src


def parse_bm(
    bm_data,
    file_number,
    width,
    height,
    palette_rgb,
    disk_number
):
    """
    Parse and decode the main BM room-background resource.

    Reads the bitmap payload and its SMAP-style strip-offset table.
    Each room is divided into 8-pixel-wide compressed strips whose
    first byte identifies the compression method. The strip table and
    room information are passed to save_room_image() for reconstruction.

    Additional diagnostic output is produced to document the strip
    structure, compression bytes, and first-strip decoding behaviour
    used while reverse-engineering the Amiga bitmap format.

    Args:
        bm_data: Complete BM chunk, including its chunk header.
        file_number: Sequential index of the embedded file on this disk.
        width: Room width obtained from the HD chunk.
        height: Room height obtained from the HD chunk.
        palette_rgb: Room palette obtained from the PA chunk.
        disk_number: Source disk number.
    """
    print("  >>> parse_bm() called")
    bm_size = int.from_bytes(bm_data[0:4], 'little')
    print(f"  Declared size: {bm_size} bytes")

    header = bm_data[4:6].decode('ascii', errors='replace')
    if header != "BM":
        print("  Invalid BM header.")
        return

    print(f"  Header found: '{header}'")

    bm_raw = bm_data[6:]
    print(f"  bm_raw: {len(bm_raw)}")

    # Show first 10 bytes in hex and ASCII
    hex_bytes = ' '.join(f'{b:02X}' for b in bm_raw[:10])
    ascii_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in bm_raw[:10])
    print(f"  First 10 bytes (hex):   {hex_bytes}")
    print(f"  First 10 bytes (ASCII): {ascii_chars}")

    strip_count = (width + 7) // 8

    smap_length = int.from_bytes(
        bm_raw[0:4],
        'little'
    )

    print(f"  SMAP length: {smap_length} bytes")
    print(f"  Room requires {strip_count} strips")

    strip_offsets = []

    for strip_index in range(strip_count):
        offset_pos = 4 + strip_index * 4

        strip_offset = int.from_bytes(
            bm_raw[offset_pos:offset_pos + 4],
            'little'
        )

        strip_offsets.append(strip_offset)

        print(
            f"    Strip {strip_index:02}: "
            f"offset {strip_offset}"
        )

    try:
        save_room_image(
            bm_raw,
            strip_offsets,
            smap_length,
            width,
            height,
            palette_rgb,
            file_number,
            disk_number
        )

    except ValueError as error:
        print(
            f"  Room image decode failed: {error}"
        )

    strip_index = 0
    strip_start = strip_offsets[strip_index]
    strip_end = strip_offsets[strip_index + 1]

    compression_code = bm_raw[strip_start]
    strip_payload = bm_raw[strip_start + 1:strip_end]

    try:
        decoded_columns, bytes_used = decode_strip_ega(
            strip_payload,
            height
        )

        print()
        print("  Decoded strip check")
        print(f"    Columns decoded:    {len(decoded_columns)}")
        print(f"    Pixels per column:  {height}")
        print(f"    Total pixels:       {8 * height}")
        print(f"    Payload bytes used: {bytes_used}")
        print(f"    Payload bytes avail:{len(strip_payload)}")

        print("    First 16 pixels of each column:")

        for column_index, column in enumerate(decoded_columns):
            pixels = ' '.join(
                f'{value:02d}'
                for value in column[:16]
            )

            print(
                f"      Column {column_index}: {pixels}"
            )

    except ValueError as error:
        print()
        print(f"  Strip decode failed: {error}")

    print()
    print("  Chunk check - first strip")
    print(f"    Strip index:       {strip_index}")
    print(f"    Strip start:       {strip_start}")
    print(f"    Strip end:         {strip_end}")
    print(f"    Total strip bytes: {strip_end - strip_start}")
    print(f"    Compression code:  0x{compression_code:02X}")
    print(f"    Payload bytes:     {len(strip_payload)}")

    preview = ' '.join(f'{b:02X}' for b in strip_payload[:32])
    print(f"    First 32 payload bytes:")
    print(f"      {preview}")

    print("  Strip compression bytes:")

    for strip_index, strip_offset in enumerate(strip_offsets):
        compression_code = bm_raw[strip_offset]

        print(
            f"    Strip {strip_index:02}: "
            f"offset {strip_offset}, "
            f"compression byte = 0x{compression_code:02X} "
            f"({compression_code})"
        )

    expected_first_offset = 4 + strip_count * 4

    print(
        f"  Expected first strip offset: "
        f"{expected_first_offset}"
    )

    print(
        f"  Actual first strip offset:   "
        f"{strip_offsets[0]}"
    )


def save_room_image(
    bm_raw,
    strip_offsets,
    smap_length,
    width,
    height,
    palette_rgb,
    file_number,
    disk_number
):
    """
    Decode and save a complete Amiga SCUMM room background.

    Decodes each 8-pixel-wide BMCOMP_PIX32 strip, assembles the strips
    horizontally into the complete room bitmap, and saves the result
    as a 16-colour indexed PNG.

    The decoder produces 4-bit colour values 0-15. For the Amiga
    version of The Secret of Monkey Island these correspond to source
    room palette entries 16-31, which are remapped to PNG palette
    entries 0-15.

    Args:
        bm_raw: BM payload containing the strip table and compressed data.
        strip_offsets: Offsets of the compressed bitmap strips.
        smap_length: Length of the bitmap/SMAP data within the BM payload.
        width: Width of the complete room bitmap in pixels.
        height: Height of the complete room bitmap in pixels.
        palette_rgb: Room palette as a list of RGB tuples.
        file_number: Sequential index used in the output filename.
        disk_number: Source disk number used for the output directory.

    Raises:
        ValueError: If the palette, strip table, compression method, or
            decoded strip data is inconsistent with the expected format.
    """
    if len(palette_rgb) < 32:
        raise ValueError(
            f"Room palette contains only {len(palette_rgb)} colours; "
            "32 are required."
        )

    strip_count = len(strip_offsets)

    if strip_count * 8 != width:
        raise ValueError(
            f"Strip count does not match room width: "
            f"{strip_count} strips = {strip_count * 8} pixels, "
            f"room width = {width}."
        )

    # Store 4-bit palette indices directly.
    pixels = [
        [0 for _ in range(width)]
        for _ in range(height)
    ]

    for strip_index, strip_start in enumerate(strip_offsets):

        if strip_index + 1 < strip_count:
            strip_end = strip_offsets[strip_index + 1]
        else:
            strip_end = smap_length

        if strip_start >= strip_end:
            raise ValueError(
                f"Strip {strip_index}: invalid range "
                f"{strip_start}..{strip_end}."
            )

        compression_code = bm_raw[strip_start]

        if compression_code != 0x0A:
            raise ValueError(
                f"Strip {strip_index}: unsupported compression "
                f"code 0x{compression_code:02X}."
            )

        strip_payload = bm_raw[
            strip_start + 1:strip_end
        ]

        columns, bytes_used = decode_strip_ega(
            strip_payload,
            height
        )

        if bytes_used != len(strip_payload):
            raise ValueError(
                f"Strip {strip_index}: decoder used {bytes_used} "
                f"of {len(strip_payload)} payload bytes."
            )

        base_x = strip_index * 8

        for column_index in range(8):
            x = base_x + column_index

            for y in range(height):
                pixels[y][x] = columns[column_index][y]

    # Create indexed-colour image.
    image = Image.new(
        'P',
        (width, height)
    )

    flat_pixels = [
        pixel
        for row in pixels
        for pixel in row
    ]

    image.putdata(flat_pixels)

    # Pillow palettes must contain up to 256 RGB entries.
    # We use source palette entries 16-31 as PNG entries 0-15.
    png_palette = []

    for r, g, b in palette_rgb[16:32]:
        png_palette.extend([r, g, b])

    # Pad remaining palette entries to 256 colours.
    png_palette.extend(
        [0, 0, 0] * (256 - 16)
    )

    image.putpalette(png_palette)

    output_dir = os.path.join(
        ROOMS_OUTPUT_DIR,
        f"disk{disk_number:02}"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    filename = os.path.join(
        output_dir,
        f'room_{file_number:02}.png'
    )

    image.save(
        filename,
        optimize=True,
        bits=4
    )

    print(
        f"  Indexed room image saved as '{filename}' "
        f"({width}x{height}, 16 colours)"
    )


def parse_oi(
    oi_data,
    file_number,
    palette_rgb,
    disk_number
):
    """
    Parse and decode an OI (Object Image) resource.

    Amiga object images use the same 8-pixel-wide BMCOMP_PIX32
    strip compression as the main room BM graphics.

    The object width is derived from the strip-offset table.
    The height is inferred by finding the value for which every
    compressed strip decodes completely and consumes exactly its
    available payload.

    Args:
        oi_data: Complete OI chunk, including its chunk header.
        file_number: Sequential index of the containing LF resource.
        palette_rgb: Palette obtained from the room's PA chunk.
        disk_number: Source disk number.
    """

    if len(oi_data) < 12:
        print("  OI chunk too short to contain image data.")
        return

    print("\n  >>> parse_oi() called")

    oi_size = int.from_bytes(
        oi_data[0:4],
        "little"
    )

    oi_id = oi_data[4:6].decode(
        "ascii",
        errors="replace"
    )

    object_id = int.from_bytes(
        oi_data[6:8],
        "little"
    )

    print(f"  Declared OI size: {oi_size} bytes")
    print(f"  Header found: '{oi_id}'")
    print(f"  Object ID: {object_id}")

    if oi_id != "OI":
        print("  Invalid OI header.")
        return

    # Bitmap data begins after the OI header and object ID.
    bitmap_data = oi_data[8:]

    if len(bitmap_data) < 8:
        print("  OI contains no usable bitmap data.")
        return

    smap_length = int.from_bytes(
        bitmap_data[0:4],
        "little"
    )

    first_strip_offset = int.from_bytes(
        bitmap_data[4:8],
        "little"
    )

    # Strip table:
    #
    #   4-byte SMAP length
    #   N × 4-byte strip offsets
    #
    # Therefore:
    #
    #   first_strip_offset = 4 + (N * 4)
    #
    if first_strip_offset < 8:
        print(
            f"  Invalid first strip offset: "
            f"{first_strip_offset}"
        )
        return

    if (first_strip_offset - 4) % 4 != 0:
        print(
            "  First strip offset does not describe "
            "a valid strip table."
        )
        return

    strip_count = (
        first_strip_offset - 4
    ) // 4

    width = strip_count * 8

    print(f"  SMAP length: {smap_length} bytes")
    print(f"  Strip count: {strip_count}")
    print(f"  Derived width: {width} pixels")

    strip_offsets = []

    for strip_index in range(strip_count):
        offset_pos = 4 + strip_index * 4

        strip_offset = int.from_bytes(
            bitmap_data[
                offset_pos:offset_pos + 4
            ],
            "little"
        )

        strip_offsets.append(strip_offset)

    # Confirm that the object uses the compression format
    # supported by our existing Amiga decoder.
    for strip_index, strip_offset in enumerate(
        strip_offsets
    ):
        if strip_offset >= len(bitmap_data):
            print(
                f"  Strip {strip_index} offset "
                f"{strip_offset} is outside OI data."
            )
            return

        compression_code = bitmap_data[
            strip_offset
        ]

        if compression_code != 0x0A:
            print(
                f"  Strip {strip_index}: unsupported "
                f"compression code "
                f"0x{compression_code:02X}."
            )
            return

    # Infer image height.
    #
    # A valid height must allow EVERY strip to:
    #
    #   1. decode exactly eight columns, and
    #   2. consume its entire compressed payload.
    #
    valid_heights = []

    for candidate_height in range(1, 257):

        valid = True

        for strip_index, strip_start in enumerate(
            strip_offsets
        ):

            if strip_index + 1 < strip_count:
                strip_end = strip_offsets[
                    strip_index + 1
                ]
            else:
                strip_end = smap_length

            strip_payload = bitmap_data[
                strip_start + 1:strip_end
            ]

            try:
                _, bytes_used = decode_strip_ega(
                    strip_payload,
                    candidate_height
                )

            except ValueError:
                valid = False
                break

            if bytes_used != len(strip_payload):
                valid = False
                break

        if valid:
            valid_heights.append(
                candidate_height
            )

    if len(valid_heights) != 1:
        print(
            "  Unable to determine a unique object "
            f"height. Candidates: {valid_heights}"
        )
        return

    height = valid_heights[0]

    print(f"  Derived height: {height} pixels")
    print(
        f"  Object image dimensions: "
        f"{width} x {height}"
    )

    save_object_image(
        bitmap_data,
        strip_offsets,
        smap_length,
        width,
        height,
        palette_rgb,
        file_number,
        object_id,
        disk_number
    )


def save_object_image(
    bitmap_data,
    strip_offsets,
    smap_length,
    width,
    height,
    palette_rgb,
    file_number,
    object_id,
    disk_number
):
    """
    Decode and save one Amiga SCUMM object image.

    The object consists of 8-pixel-wide BMCOMP_PIX32 strips using
    the same 4-bit colour decoding as room backgrounds.

    Args:
        bitmap_data: OI bitmap payload containing the strip table.
        strip_offsets: Offsets of compressed image strips.
        smap_length: Length of the object's bitmap data.
        width: Derived object width in pixels.
        height: Derived object height in pixels.
        palette_rgb: Palette obtained from the containing room.
        file_number: Sequential LF index containing the object.
        object_id: SCUMM object identifier stored in the OI.
        disk_number: Source disk number.
    """

    pixels = [
        [0 for _ in range(width)]
        for _ in range(height)
    ]

    strip_count = len(strip_offsets)

    for strip_index, strip_start in enumerate(
        strip_offsets
    ):

        if strip_index + 1 < strip_count:
            strip_end = strip_offsets[
                strip_index + 1
            ]
        else:
            strip_end = smap_length

        compression_code = bitmap_data[
            strip_start
        ]

        if compression_code != 0x0A:
            raise ValueError(
                f"Object {object_id}, strip "
                f"{strip_index}: unsupported "
                f"compression code "
                f"0x{compression_code:02X}."
            )

        strip_payload = bitmap_data[
            strip_start + 1:strip_end
        ]

        columns, bytes_used = decode_strip_ega(
            strip_payload,
            height
        )

        if bytes_used != len(strip_payload):
            raise ValueError(
                f"Object {object_id}, strip "
                f"{strip_index}: decoder used "
                f"{bytes_used} of "
                f"{len(strip_payload)} bytes."
            )

        base_x = strip_index * 8

        for column_index in range(8):

            x = base_x + column_index

            for y in range(height):
                pixels[y][x] = (
                    columns[column_index][y]
                )

    image = Image.new(
        "P",
        (width, height)
    )

    image.putdata(
        [
            pixel
            for row in pixels
            for pixel in row
        ]
    )

    # As with BM room backgrounds, decoded values 0-15
    # map to source room palette entries 16-31.
    png_palette = []

    for r, g, b in palette_rgb[16:32]:
        png_palette.extend(
            [r, g, b]
        )

    png_palette.extend(
        [0, 0, 0] * (256 - 16)
    )

    image.putpalette(
        png_palette
    )

    output_dir = os.path.join(
        OBJECTS_OUTPUT_DIR,
        f"disk{disk_number:02}",
        f"room_{file_number:02}"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    filename = os.path.join(
        output_dir,
        f"object_{object_id:03}.png"
    )

    image.save(
        filename,
        optimize=True,
        bits=4
    )

    print(
        f"  Indexed object image saved as "
        f"'{filename}' "
        f"({width}x{height}, 16 colours)"
    )


def decode_costume_cel_ami(cel_payload, width, height):
    """
    Decode one 16-colour Amiga SCUMM costume cel.

    Costume pixels are stored using BYLE RLE. The high nibble
    identifies the colour and the low nibble gives the run length.
    A zero run nibble means the following byte contains the length.

    Amiga costume pixels are decoded vertically, column by column.

    Args:
        cel_payload: Compressed costume cel pixel data.
        width: Cel width in pixels.
        height: Cel height in pixels.

    Returns:
        A tuple containing:
            - A flat row-major list of decoded colour indices suitable
              for Pillow.
            - The number of compressed bytes consumed.

    Raises:
        ValueError: If the compressed data ends before the complete
            cel has been decoded.
    """

    rows = [
        [0 for _ in range(width)]
        for _ in range(height)
    ]

    src = 0
    x = 0
    y = 0

    def write_pixel(colour):
        nonlocal x, y

        if x >= width:
            raise ValueError(
                "Costume decoder attempted to write beyond "
                "the cel width."
            )

        rows[y][x] = colour

        y += 1

        if y >= height:
            y = 0
            x += 1

    while x < width:

        if src >= len(cel_payload):
            raise ValueError(
                "Costume cel data ended before all pixels "
                "were decoded."
            )

        value = cel_payload[src]
        src += 1

        colour = value >> 4
        run = value & 0x0F

        if run == 0:
            if src >= len(cel_payload):
                raise ValueError(
                    "Missing extended costume run length."
                )

            run = cel_payload[src]
            src += 1

        for _ in range(run):
            write_pixel(colour)

    pixels = [
        pixel
        for row in rows
        for pixel in row
    ]

    return pixels, src


def parse_co(
    co_data,
    room_palette,
    disk_number,
    room_number,
    costume_number,
    costume_stats
):
    """
    Parse and extract graphical cels from a classic SCUMM CO costume.

    This implementation targets the 16-colour 0x58 costume format
    used by the Amiga version of The Secret of Monkey Island.

    The costume contains animation tables that ultimately reference
    graphical cels. Each unique referenced cel is decoded once and
    written as a separate indexed PNG.

    Args:
        co_data: Complete CO chunk, including its small-header wrapper.
        room_palette: Palette belonging to the associated room.
        disk_number: Source disk number.
        room_number: Sequential room index within the disk.
        costume_number: Sequential CO index within the LF resource.
        costume_stats: Statistics dictionary used to record costume
            extraction results and problems.
    """

    if len(co_data) < 24:
        print("  CO chunk too short.")
        return

    declared_size = int.from_bytes(
        co_data[0:4],
        "little"
    )

    header = co_data[4:6].decode(
        "ascii",
        errors="replace"
    )

    if header != "CO":
        print(
            f"  Invalid CO header: '{header}'"
        )
        return

    costume_stats["costumes_processed"] += 1

    num_anim = co_data[6]
    format_byte = co_data[7]

    costume_format = format_byte & 0x7F
    mirrored = bool(format_byte & 0x80)

    print()
    print("  >>> parse_co() called")
    print(f"  Declared CO size: {declared_size} bytes")
    print(f"  Costume format: 0x{costume_format:02X}")
    print(f"  Maximum animation index: {num_anim}")
    print(f"  Mirrored: {mirrored}")

    if costume_format != 0x58:
        print(
            "  Unsupported costume format; "
            "expected 0x58."
        )

        costume_stats["unsupported_formats"] += 1

        costume_stats["problems"].append({
            "disk": disk_number,
            "room": room_number,
            "costume": costume_number,
            "cel": None,
            "message": (
                f"unsupported costume format "
                f"0x{costume_format:02X}"
            )
        })

        return

    costume_palette = list(
        co_data[8:24]
    )

    table_base = 24

    # Offset to the animation command stream.
    anim_cmds_offset = int.from_bytes(
        co_data[
            table_base:table_base + 2
        ],
        "little"
    )

    # Sixteen limb-specific frame-table offsets follow.
    frame_offsets_base = table_base + 2

    # Animation data-offset table follows the 16 frame offsets.
    data_offsets_base = table_base + 34

    if anim_cmds_offset >= len(co_data):
        print(
            "  Animation command table lies outside CO."
        )
        return

    print(
        f"  Animation command table offset: "
        f"{anim_cmds_offset}"
    )

    referenced_commands = set()

    # Discover which animation command indices are referenced
    # by the costume's limb data.
    for animation_index in range(num_anim + 1):

        entry = (
            data_offsets_base
            + animation_index * 2
        )

        if entry + 2 > len(co_data):
            break

        animation_offset = int.from_bytes(
            co_data[
                entry:entry + 2
            ],
            "little"
        )

        if animation_offset == 0:
            continue

        if animation_offset + 2 > len(co_data):
            continue

        pointer = animation_offset

        limb_mask = int.from_bytes(
            co_data[
                pointer:pointer + 2
            ],
            "little"
        )

        pointer += 2

        limb = 0
        mask = limb_mask

        while mask & 0xFFFF:

            if mask & 0x8000:

                if pointer + 2 > len(co_data):
                    break

                command_start = int.from_bytes(
                    co_data[
                        pointer:pointer + 2
                    ],
                    "little"
                )

                pointer += 2

                if command_start != 0xFFFF:

                    if pointer >= len(co_data):
                        break

                    extra = co_data[pointer]
                    pointer += 1

                    command_end = (
                        command_start
                        + (extra & 0x7F)
                    )

                    for command_index in range(
                        command_start,
                        command_end + 1
                    ):
                        referenced_commands.add(
                            (limb, command_index)
                        )

            limb += 1
            mask = (mask << 1) & 0xFFFF

    # Convert referenced animation commands into candidate cel offsets.
    cel_offsets = set()

    for limb, command_index in sorted(
        referenced_commands
    ):

        command_pos = (
            anim_cmds_offset
            + command_index
        )

        if command_pos >= len(co_data):
            continue

        command = co_data[command_pos] & 0x7F

        # 0x79 and above are control/animation commands,
        # not drawable cel indices.
        if command >= 0x79:
            continue

        frame_offset_entry = (
            frame_offsets_base
            + limb * 2
        )

        if frame_offset_entry + 2 > len(co_data):
            continue

        frame_table_offset = int.from_bytes(
            co_data[
                frame_offset_entry:
                frame_offset_entry + 2
            ],
            "little"
        )

        if frame_table_offset == 0:
            continue

        cel_pointer_entry = (
            frame_table_offset
            + command * 2
        )

        if cel_pointer_entry + 2 > len(co_data):
            continue

        cel_offset = int.from_bytes(
            co_data[
                cel_pointer_entry:
                cel_pointer_entry + 2
            ],
            "little"
        )

        # A valid cel must have room for its 12-byte header.
        if cel_offset < 24:
            continue

        if cel_offset + 12 > len(co_data):
            continue

        cel_offsets.add(
            cel_offset
        )

    cel_offsets = sorted(cel_offsets)

    costume_stats["cel_candidates"] += len(
        cel_offsets
    )

    print(
        f"  Unique graphical cels found: "
        f"{len(cel_offsets)}"
    )

    for cel_index, cel_offset in enumerate(
        cel_offsets,
        start=1
    ):

        width = int.from_bytes(
            co_data[
                cel_offset:cel_offset + 2
            ],
            "little"
        )

        height = int.from_bytes(
            co_data[
                cel_offset + 2:cel_offset + 4
            ],
            "little"
        )

        rel_x = read_signed_le16(
            co_data,
            cel_offset + 4
        )

        rel_y = read_signed_le16(
            co_data,
            cel_offset + 6
        )

        move_x = read_signed_le16(
            co_data,
            cel_offset + 8
        )

        move_y = read_signed_le16(
            co_data,
            cel_offset + 10
        )

        print(
            f"    Cel {cel_index:03}: "
            f"{width}x{height}, "
            f"rel=({rel_x},{rel_y}), "
            f"move=({move_x},{move_y})"
        )

        # ----------------------------------------------------------
        # Sanity checks
        # ----------------------------------------------------------

        if width == 0 or height == 0:
            print(
                f"    Skipping invalid cel dimensions: "
                f"{width}x{height}"
            )

            costume_stats["zero_size"] += 1

            costume_stats["problems"].append({
                "disk": disk_number,
                "room": room_number,
                "costume": costume_number,
                "cel": cel_index,
                "message": (
                    f"invalid cel dimensions "
                    f"{width}x{height}"
                )
            })

            continue

        if (
            width > 1024
            or height > 1024
            or width * height > 500000
        ):
            print(
                f"    Skipping implausible cel dimensions: "
                f"{width}x{height}"
            )

            costume_stats["implausible_size"] += 1

            costume_stats["problems"].append({
                "disk": disk_number,
                "room": room_number,
                "costume": costume_number,
                "cel": cel_index,
                "message": (
                    f"implausible cel dimensions "
                    f"{width}x{height}"
                )
            })

            continue

        payload_start = (
            cel_offset + 12
        )

        # Do not stop at the next candidate cel offset.
        # Let the decoder consume exactly as much compressed data
        # as is required to produce width * height pixels.
        cel_payload = co_data[
            payload_start:
        ]

        try:
            pixels, bytes_used = (
                decode_costume_cel_ami(
                    cel_payload,
                    width,
                    height
                )
            )

        except ValueError as error:
            print(
                f"    Cel decode failed: {error}"
            )

            costume_stats["decode_failures"] += 1

            costume_stats["problems"].append({
                "disk": disk_number,
                "room": room_number,
                "costume": costume_number,
                "cel": cel_index,
                "message": (
                    f"decode failed: {error}"
                )
            })

            continue

        print(
            f"    Compressed bytes used: "
            f"{bytes_used}"
        )

        try:
            save_costume_cel(
                pixels,
                width,
                height,
                costume_palette,
                room_palette,
                disk_number,
                room_number,
                costume_number,
                cel_index
            )

            costume_stats["cels_saved"] += 1

        except ValueError as error:
            print(
                f"    Costume cel save failed: "
                f"{error}"
            )

            costume_stats["save_failures"] += 1

            costume_stats["problems"].append({
                "disk": disk_number,
                "room": room_number,
                "costume": costume_number,
                "cel": cel_index,
                "message": (
                    f"save failed: {error}"
                )
            })


def save_costume_cel(
    pixels,
    width,
    height,
    costume_palette,
    room_palette,
    disk_number,
    room_number,
    costume_number,
    cel_number
):
    """
    Save a decoded costume cel as a transparent indexed PNG.

    Costume colour indices map through the costume's own 16-entry
    palette table into the containing room's palette.

    Colour index 0 is treated as transparent.

    Args:
        pixels: Flat list of decoded 4-bit costume colour indices.
        width: Cel width in pixels.
        height: Cel height in pixels.
        costume_palette: Sixteen room-palette indices from the CO.
        room_palette: Room palette as RGB tuples.
        disk_number: Source disk number.
        room_number: Sequential room index within the source disk.
        costume_number: Sequential CO index within the LF resource.
        cel_number: Sequential unique cel number within the costume.
    """

    image = Image.new(
        "P",
        (width, height)
    )

    image.putdata(pixels)

    png_palette = []

    for palette_index in costume_palette:
        if palette_index >= len(room_palette):
            raise ValueError(
                f"Costume palette index {palette_index} "
                f"is outside the room palette."
            )

        r, g, b = room_palette[palette_index]
        png_palette.extend([r, g, b])

    png_palette.extend(
        [0, 0, 0] * (256 - 16)
    )

    image.putpalette(png_palette)

    output_dir = os.path.join(
        COSTUMES_OUTPUT_DIR,
        f"disk{disk_number:02}",
        f"room_{room_number:02}",
        f"costume_{costume_number:02}"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    filename = os.path.join(
        output_dir,
        f"cel_{cel_number:03}.png"
    )

    image.save(
        filename,
        optimize=True,
        bits=4,
        transparency=0
    )

    print(
        f"    Costume cel saved as '{filename}' "
        f"({width}x{height})"
    )


# Entry point
if __name__ == '__main__':

    print(
        f"MonkeyIslandAmigaGraphics "
        f"v{__version__}"
    )

    costume_stats = create_costume_stats()

    for disk_number in range(1, 5):
        filepath = (
            f'resource/disk{disk_number:02}.lec'
        )

        print()
        print("=" * 70)
        print(f"Processing {filepath}")
        print("=" * 70)

        parse_lec_header_and_fo(
            filepath,
            disk_number,
            costume_stats
        )

    print_costume_summary(
        costume_stats
    )
