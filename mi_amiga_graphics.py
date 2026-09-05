import os
from PIL import Image, ImageDraw, ImageFont


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


def parse_lec_header_and_fo(filepath):
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
        parse_lf(lf_data, i + 1, fo_id_byte)


def parse_lf(lf_data, file_index, fo_id_byte):
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
    chunk_counts = {}

    print("  Contained chunks:")
    while pointer + 6 <= len(lf_data):
        chunk_size = int.from_bytes(lf_data[pointer:pointer + 4], 'little')
        chunk_id = lf_data[pointer + 4:pointer + 6].decode('ascii', errors='ignore')
        label = CHUNK_LABELS.get(chunk_id, '?')

        print(f"    Offset {pointer:>5}: ID='{chunk_id}', Label='{label}', Size={chunk_size} bytes")
        contents.append((pointer, chunk_id, chunk_size))
        chunk_counts[chunk_id] = chunk_counts.get(chunk_id, 0) + 1
        pointer += chunk_size

        if pointer == len(lf_data):
            print("  End of LF block reached cleanly.")
            break
        elif pointer > len(lf_data):
            print("  Warning: last chunk extends beyond LF block.")
            break

    # Look for RO chunks and process each
    for offset, chunk_id, chunk_size in contents:
        if chunk_id == 'RO':
            ro_data = lf_data[offset:offset + chunk_size]
            parse_ro(ro_data, file_index)


def parse_ro(ro_data, file_index):
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

    # Values required later by the BM decoder.
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
                file_index
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
                palette_rgb
            )


def parse_hd(hd_data):
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


def parse_pa(pa_data, room_index=None):
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
    os.makedirs("Palettes", exist_ok=True)
    swatch_size = 50
    padding = 10
    font_size = 10
    cols = 8
    rows = (colour_count + cols - 1) // cols
    img_width = cols * swatch_size
    img_height = rows * (swatch_size + font_size * 2)

    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.load_default()
    except:
        font = None

    for idx, (r, g, b) in enumerate(colours):
        x = (idx % cols) * swatch_size
        y = (idx // cols) * (swatch_size + font_size * 2)
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=(r, g, b))
        hex_text = f"#{r:02X}{g:02X}{b:02X}"
        dec_text = f"{r},{g},{b}"
        draw.text((x + 2, y + swatch_size), hex_text, fill='black', font=font)
        draw.text((x + 2, y + swatch_size + font_size), dec_text, fill='black', font=font)

    filename = f"Palettes/palette_{room_index if room_index is not None else 'unknown'}.png"
    img.save(filename)
    print(f"    Palette image saved as '{filename}'")

    return colours


def decode_strip_ega(strip_payload, height):
    """
    Decode one 8-pixel-wide SCUMM EGA-style strip.

    This is a Python adaptation of ScummVM's drawStripEGA()
    routine, used by BMCOMP_PIX32 (0x0A) for the Amiga
    version of The Secret of Monkey Island.

    Returns:
        columns: 8 columns of palette-index nibbles (0-15)
        src:     number of payload bytes consumed
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


def save_room_image(
    bm_raw,
    strip_offsets,
    smap_length,
    width,
    height,
    palette_rgb,
    file_number
):
    """
    Decode all BMCOMP_PIX32 strips and assemble the room image.

    The Amiga version of The Secret of Monkey Island decodes to
    4-bit colour values (0-15), which map to room palette entries
    16-31.

    The resulting PNG is saved as an indexed-colour image using
    exactly those 16 room colours.
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

    os.makedirs(
        'Rooms',
        exist_ok=True
    )

    filename = f'Rooms/room_{file_number}.png'

    image.save(
        filename,
        optimize=True
    )

    print(
        f"  Indexed room image saved as '{filename}' "
        f"({width}x{height}, 16 colours)"
    )


def parse_bm(bm_data, file_number, width, height, palette_rgb):
    print("  >>> parse_bm() called")
    bm_size = int.from_bytes(bm_data[0:4], 'little')
    print(f"  Declared size: {bm_size} bytes")

    header = bm_data[4:6].decode('ascii', errors='replace')
    print(f"  Header found: '{header}'")

    bm_raw = bm_data[6:]
    print(f"  bm_raw: {len(bm_raw)}")

    # Show first 10 bytes in hex and ASCII
    hex_bytes = ' '.join(f'{b:02X}' for b in bm_raw[:10])
    ascii_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in bm_raw[:10])
    print(f"  First 10 bytes (hex):   {hex_bytes}")
    print(f"  First 10 bytes (ASCII): {ascii_chars}")

    # Save bm_raw for manual inspection
    os.makedirs("bm_raw", exist_ok=True)
    with open(f"bm_raw/bm_raw_{file_number}.bin", "wb") as f:
        f.write(bm_raw)

    # Try decoding and rendering images from 4-bitplane RLE
    #save_bitplane_images_and_combined(bm_raw, width, height, 4, file_number, palette_rgb)
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
            file_number
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


def decode_scumm_rle(bm_raw, width, height, bitplanes):
    row_bytes = ((width + 15) // 16) * 2
    plane_size = row_bytes * height
    decoded_planes = []

    src_pointer = 0
    for plane_index in range(bitplanes):
        plane_data = bytearray()
        bytes_written = 0

        while bytes_written < plane_size:
            byte = bm_raw[src_pointer]
            src_pointer += 1

            if byte == 0:
                count = bm_raw[src_pointer]
                src_pointer += 1
                plane_data.extend([0] * count)
                bytes_written += count
            else:
                plane_data.append(byte)
                bytes_written += 1

        decoded_planes.append(plane_data)

    return decoded_planes


def extract_bitplane_image(plane_data, width, height):
    row_bytes = ((width + 15) // 16) * 2
    img = Image.new('L', (width, height))
    pixels = img.load()

    for y in range(height):
        for x_byte in range(row_bytes):
            byte = plane_data[y * row_bytes + x_byte]
            for bit in range(8):
                bit_index = 7 - bit
                x = x_byte * 8 + bit_index
                if x < width:
                    value = 255 if (byte & (1 << bit)) else 0
                    pixels[x, y] = value
    return img


def combine_bitplanes(bitplanes, width, height):
    img = Image.new('P', (width, height))
    pixels = img.load()

    row_bytes = ((width + 15) // 16) * 2
    for y in range(height):
        for x_byte in range(row_bytes):
            bits = [p[y * row_bytes + x_byte] for p in bitplanes]
            for bit in range(8):
                bit_index = 7 - bit
                x = x_byte * 8 + bit_index
                if x < width:
                    colour_index = 0
                    for i, plane in enumerate(bitplanes):
                        if bits[i] & (1 << bit):
                            colour_index |= (1 << i)
                    pixels[x, y] = colour_index
    return img


def set_palette_amiga(image, palette_rgb):
    flat_palette = [val for rgb in palette_rgb[:16] for val in rgb]
    image.putpalette(flat_palette + [0] * (768 - len(flat_palette)))


def save_bitplane_images_and_combined(bm_raw, width, height, bitplanes, file_number, palette_rgb):
    os.makedirs("Bitplane_Images", exist_ok=True)

    planes = decode_scumm_rle(bm_raw, width, height, bitplanes)

    for i, plane_data in enumerate(planes):
        img = extract_bitplane_image(plane_data, width, height)
        img.save(f"Bitplane_Images/bitplane_{file_number}_{i}.png")

    final_img = combine_bitplanes(planes, width, height)
    set_palette_amiga(final_img, palette_rgb)
    final_img.save(f"Bitplane_Images/final_combined_{file_number}.png")


# Entry point
if __name__ == '__main__':
    parse_lec_header_and_fo('resource/disk01.lec')
