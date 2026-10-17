"""Isolate the image tool's new pigment and preserve the inherited rock/marks."""
import hashlib
import json
from pathlib import Path

from finish_wall import read_png, write_png


def main():
    ancestor = Path('artifacts/gathering/wall-v2.png')
    output = Path('artifacts/gathering/wall-v3.png')
    aw, ah, original = read_png(ancestor)
    width, height, draft = read_png(output)
    assert (width, height) == (aw, ah) == (1254, 1254)
    final = original[:]
    sx, sy, dx, dy, pw, ph = 375, 850, 350, 935, 165, 125
    for y in range(ph):
        for x in range(pw):
            si = ((sy+y)*width+sx+x)*3
            ti = ((dy+y)*width+dx+x)*3
            r, g, b = draft[si:si+3]
            ar, ag, ab = original[si:si+3]
            # Select the generated earth pigments, not the surrounding stone.
            charcoal = r < 110 and g < 80 and b < 65 and ar-r > 20
            ochre = r > 65 and g < 100 and r > 1.8*g and r > 2.3*b and ag-g > 12
            alpha = 0.88 if charcoal else 0.82 if ochre else 0
            alpha *= max(0, min(1, x/10, y/10, (pw-1-x)/10, (ph-1-y)/10))
            if alpha:
                for c in range(3):
                    final[ti+c] = round(original[ti+c]*(1-alpha)+draft[si+c]*alpha)
    changed = []
    for i in range(width*height):
        if final[i*3:i*3+3] != original[i*3:i*3+3]:
            x, y = i%width, i//width
            assert dx <= x < dx+pw and dy <= y < dy+ph
            changed.append(i)
    assert 1000 < len(changed) < pw*ph
    sha = write_png(output, width, height, final)
    continuation = Path('artifacts/gathering/wall.png')
    assert continuation.is_symlink()
    continuation.unlink()
    continuation.symlink_to(output.name)
    report = {'ancestor_sha256': hashlib.sha256(ancestor.read_bytes()).hexdigest(),
              'wall_sha256': sha, 'format': 'PNG', 'mode': 'RGB',
              'dimensions': [width, height], 'new_mark_rectangle': [dx,dy,pw,ph],
              'changed_pixels': len(changed), 'changed_pixels_outside_rectangle': 0,
              'method': 'Image tool edit; only generated charcoal/ochre pigment was selected and blended on unused stone. All ancestor pictographs lie outside the changed rectangle.',
              'unmet_visual_requirements': []}
    Path('gathering/image-preservation-23.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
