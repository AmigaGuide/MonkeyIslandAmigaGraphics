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
        chunk_size = int.from_bytes(ro_data[pointer:pointer + 4], 'little')
        chunk_id = ro_data[pointer + 4:pointer + 6].decode('ascii', errors='ignore')
        label = CHUNK_LABELS.get(chunk_id, '?')

        print(f"    Offset {pointer:>5}: ID='{chunk_id}', Label='{label}', Size={chunk_size} bytes")
        contents.append((pointer, chunk_id, chunk_size))
        chunk_counts[chunk_id] = chunk_counts.get(chunk_id, 0) + 1
        pointer += chunk_size

        if pointer == len(ro_data):
            print("  End of RO block reached cleanly.")
            break
        elif pointer > len(ro_data):
            print("  Warning: last subchunk extends beyond RO block.")
            break

    print("  Subchunk counts:")
    for chunk_id, count in chunk_counts.items():
        label = CHUNK_LABELS.get(chunk_id, '?')
        print(f"    {chunk_id}: {count} ({label})")

    if chunk_counts.get('BM', 0) == 0:
        print("  No BM chunk found — skipping detailed parsing.")
        return

    for offset, chunk_id, chunk_size in contents:
        if chunk_id == 'HD':
            hd_data = ro_data[offset : offset + chunk_size]
            parse_hd(hd_data)
        elif chunk_id == 'PA':
            pa_data = ro_data[offset : offset + chunk_size]
            parse_pa(pa_data, file_index)
        elif chunk_id == 'BM':
            bm_data = ro_data[offset : offset + chunk_size]
            #parse_bm(bm_data)
            parse_bm(bm_data, file_index)


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


def parse_bm(bm_data, file_index):
    print("\n  >>> parse_bm() called")
    print(f"  Declared size: {len(bm_data)} bytes")

    chunk_id = bm_data[4:6].decode('ascii', errors='ignore')
    if chunk_id != 'BM':
        print(f"  Warning: Expected 'BM' header, found '{chunk_id}'")
        return

    bm_raw = bm_data[6:]
    print(f"  bm_raw: {len(bm_raw)} bytes")

    # Show first 10 bytes in hex and ASCII
    hex_bytes = ' '.join(f'{b:02X}' for b in bm_raw[:10])
    ascii_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in bm_raw[:10])
    print(f"  First 10 bytes (hex):   {hex_bytes}")
    print(f"  First 10 bytes (ASCII): {ascii_chars}")

    # Save the raw RLE image data to disk
    os.makedirs("Bitmaps", exist_ok=True)
    output_path = f"Bitmaps/bm_raw_{file_index}.bin"
    with open(output_path, "wb") as f:
        f.write(bm_raw)
    print(f"  Raw BM data written to: {output_path}")



# Entry point
if __name__ == '__main__':
    parse_lec_header_and_fo('disk01.lec')
