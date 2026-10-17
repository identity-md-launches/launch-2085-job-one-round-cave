#!/usr/bin/env python3
"""Conserve ancestor pixels around the image tool's new pictograph.

One-shot build helper; run before replacing wall.png with wall-v3.png.
PNG codec adapted from the inherited gathering/finish_wall.py (read as data).
Only the generated ring and stones are composited; no artwork is synthesized.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib

def read_png(path):
    raw = path if isinstance(path, bytes) else Path(path).read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    at, packed = 8, bytearray()
    while at < len(raw):
        size = int.from_bytes(raw[at:at + 4], 'big')
        kind, body = raw[at + 4:at + 8], raw[at + 8:at + 8 + size]
        checksum = int.from_bytes(raw[at + 8 + size:at + 12 + size], 'big')
        if zlib.crc32(kind + body) != checksum:
            raise ValueError('PNG checksum mismatch')
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
            if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ValueError('expected noninterlaced 8-bit RGB PNG')
        elif kind == b'IDAT':
            packed.extend(body)
        elif kind == b'IEND':
            break
        at += size + 12
    data = zlib.decompress(packed)
    stride = width * 3
    if len(data) != height * (stride + 1):
        raise ValueError('PNG data length mismatch')
    result, previous = bytearray(), bytearray(stride)
    for y in range(height):
        at = y * (stride + 1)
        mode, row = data[at], bytearray(data[at + 1:at + stride + 1])
        for x in range(stride):
            left = row[x - 3] if x >= 3 else 0
            above = previous[x]
            upper_left = previous[x - 3] if x >= 3 else 0
            if mode == 0:
                predictor = 0
            elif mode == 1:
                predictor = left
            elif mode == 2:
                predictor = above
            elif mode == 3:
                predictor = (left + above) // 2
            elif mode == 4:
                p = left + above - upper_left
                distances = (abs(p - left), abs(p - above), abs(p - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            else:
                raise ValueError('unsupported PNG filter')
            row[x] = (row[x] + predictor) & 255
        result.extend(row)
        previous = row
    return width, height, result


def write_png(path, width, height, pixels):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\0' + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))
    Path(path).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def main():
    ancestor = Path('artifacts/line-4/wall.png')
    output = Path('artifacts/line-4/wall-v3.png')
    ancestor_sha = hashlib.sha256(ancestor.read_bytes()).hexdigest()
    if ancestor_sha != '744178408ffe88c1b2141c369151c45a0fca1edfc0dbbde502194526385f6c62':
        raise ValueError('expected inherited wall; do not apply twice')
    width, height, original = read_png(ancestor)
    dw, dh, draft = read_png(output)
    assert (width, height) == (dw, dh) == (1254, 1254)
    final = original[:]
    # Masks enclose only the image-generated pictograph, away from old pigment.
    for y in range(620, 745):
        for x in range(775, 1012):
            outer = ((x - 866) / 88) ** 2 + ((y - 683) / 60) ** 2
            inner = ((x - 866) / 72) ** 2 + ((y - 683) / 44) ** 2
            ring = outer < 1 and inner > 1
            stones = any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < 1
                         for cx, cy, rx, ry in [(832, 685, 30, 33),
                                               (899, 682, 34, 33),
                                               (985, 699, 24, 27)])
            if ring or stones:
                at = (y * width + x) * 3
                final[at:at + 3] = draft[at:at + 3]
    points = [(i % width, i // width) for i in range(width * height)
              if final[3*i:3*i+3] != original[3*i:3*i+3]]
    assert points and all(775 <= x < 1012 and 620 <= y < 745 for x, y in points)
    sha = write_png(output, width, height, final)
    evidence = {'ancestor_sha256': ancestor_sha, 'wall_sha256': sha,
                'dimensions': [width, height], 'format': 'PNG',
                'changed_pixels': len(points),
                'changed_bounds_xyxy': [min(x for x,y in points), min(y for x,y in points),
                                        max(x for x,y in points), max(y for x,y in points)],
                'changed_pixels_outside_new_mark_region': 0,
                'method': 'Image-generated pigment regions composited onto the inherited wall. '
                          'Every pixel outside those masks is identical to the ancestor.'}
    Path('line-4/IMAGE-22.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
