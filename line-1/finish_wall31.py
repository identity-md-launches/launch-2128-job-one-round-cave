"""Consume generated pigment at wall-v12.png; preserve all ancestral painting."""
import hashlib
import json
from pathlib import Path
from finish_wall24 import read_png, write_png, thumbnail


def main():
    wall = Path('artifacts/line-1/wall.png')
    output = Path('artifacts/line-1/wall-v12.png')
    ancestor = wall.read_bytes()
    ancestor_hash = hashlib.sha256(ancestor).hexdigest()
    assert ancestor_hash == 'da1c35f021088696a2a6b5f2ffb9ee6b68be4ea3fa6e9ff93a6c0f86756d2439'
    assert ancestor == Path('artifacts/line-1/wall-v11.png').read_bytes()
    width, height, old = read_png(ancestor)
    gw, gh, pigment = read_png(output)
    assert (width, height) == (1254, 1254)
    assert (gw, gh) == (1536, 1024)
    final = old[:]
    x0, y0, mw, mh = 610, 205, 240, 100
    sx0, sy0, sw, sh = 20, 270, 1496, 490
    for y in range(mh):
        for x in range(mw):
            sx, sy = sx0 + int(x * sw / mw), sy0 + int(y * sh / mh)
            rgb = pigment[(sy * gw + sx) * 3:(sy * gw + sx) * 3 + 3]
            strength = max(rgb)
            if strength < 30:
                continue
            alpha = min(.80, (strength - 30) / 175)
            alpha *= min(1, x / 4, y / 4, (mw - 1 - x) / 4, (mh - 1 - y) / 4)
            i = ((y0 + y) * width + x0 + x) * 3
            for channel in range(3):
                final[i + channel] = round(old[i + channel] * (1 - alpha) + rgb[channel] * alpha)
    changed = outside = 0
    for pixel in range(width * height):
        if old[pixel * 3:pixel * 3 + 3] != final[pixel * 3:pixel * 3 + 3]:
            changed += 1
            x, y = pixel % width, pixel // width
            outside += not (x0 <= x < x0 + mw and y0 <= y < y0 + mh)
    assert changed and outside == 0
    sha = write_png(output, width, height, final)
    assert read_png(output)[2] == final
    wall.write_bytes(output.read_bytes())
    jpeg = Path('dist/line-1/31.jpg')
    assert not jpeg.exists()
    thumbnail(output.read_bytes(), jpeg)
    report = {
        'ancestor_sha256': ancestor_hash, 'wall_sha256': sha,
        'wall_paths': [str(output), str(wall)], 'dimensions': [width, height],
        'format': 'PNG', 'mode': 'RGB',
        'thumbnail': {'path': str(jpeg), 'dimensions': [512, 512],
                      'format': 'JPEG', 'bytes': jpeg.stat().st_size},
        'mark_rectangle': [x0, y0, mw, mh], 'changed_pixels': changed,
        'changed_pixels_outside_rectangle': outside,
        'method': 'Built-in imagegen motif; only generated pigment blended into unused rock.',
        'visual_review': 'Pending explicit full-wall and JPEG inspection.',
        'unmet_visual_requirements': [],
        'location_conflict': 'Followed the specific required dist/line-1/31.jpg path despite the general no-pictures-outside-artifacts sentence.'}
    Path('line-1/IMAGE-31.json').write_text(json.dumps(report, indent=2) + '\n')
    assert len(list(Path('dist/line-1').glob('*.json'))) == 30
    record = {'name': 'Two cords claim one peg',
              'image': 'https://api.imd.fun/artifacts/' + sha,
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Crystal'},
                  {'trait_type': 'Wall', 'value': 'Line 1'},
                  {'trait_type': 'Number', 'value': 31},
                  {'trait_type': 'Left behind', 'value': 'Binding Review'},
                  {'trait_type': 'Meaning', 'value': 'A chalk eye watches two cords claim the same peg.'},
                  {'trait_type': 'One thing', 'value': 'Reviewable three-way text merging'}]}
    Path('dist/line-1/31.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
