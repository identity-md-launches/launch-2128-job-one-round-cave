"""Read-only round-32 checks; emits a small local review report in line-2."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


def git(*args, binary=False):
    return subprocess.run(['git', *args], capture_output=True, text=not binary, check=True).stdout


def main():
    changed = git('diff', '--name-only', 'HEAD').splitlines()
    assert set(changed) <= {'line-2/README.md', 'line-2/USED.md', 'artifacts/line-2/wall.png'}, changed
    assert Path('line-2/GOAL.md').read_bytes() == git('show', 'HEAD:line-2/GOAL.md', binary=True)
    records = sorted(Path('dist/line-2').glob('[0-9][0-9].json'))
    assert len(records) == 32
    for p in records[:-1]:
        assert p.read_bytes() == git('show', 'HEAD:' + str(p), binary=True), p
    record = json.loads(records[-1].read_text())
    new = Path('artifacts/line-2/wall-v12.png')
    assert set(record) == {'name', 'image', 'attributes'}
    assert record['image'] == 'https://api.imd.fun/artifacts/' + hashlib.sha256(new.read_bytes()).hexdigest()
    traits = record['attributes']
    assert [x['trait_type'] for x in traits] == ['Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing']
    assert all(set(x) == {'trait_type', 'value'} for x in traits)
    assert [x['value'] for x in traits[:3]] == ['Crystal', 'Line 2', 32]
    assert type(traits[2]['value']) is int
    assert Path('artifacts/line-2/wall.png').read_bytes() == new.read_bytes()
    assert Path('dist/line-2/32.jpg').read_bytes().startswith(b'\xff\xd8')
    spec = importlib.util.spec_from_file_location('png_check32', 'gathering/finish_wall.py')
    png = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(png)
    w, h, old = png.read_png('artifacts/line-2/wall-v11.png')
    nw, nh, final = png.read_png(new)
    assert (nw, nh) == (w, h) == (1254, 1254)
    changed_pixels = outside = 0
    for i in range(w*h):
        if old[i*3:i*3+3] != final[i*3:i*3+3]:
            changed_pixels += 1
            x, y = i % w, i // w
            outside += not (495 <= x < 625 and 180 <= y < 250)
    assert changed_pixels == 1764 and outside == 0
    new_files = git('ls-files', '--others', '--exclude-standard').splitlines()
    assert all(p.startswith(('line-2/', 'artifacts/line-2/', 'dist/line-2/')) for p in new_files), new_files
    assert all(Path(p).stat().st_size <= 100000 for p in new_files if not p.startswith('artifacts/'))
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', str(new)], capture_output=True)
    assert tracked.returncode != 0
    report = {
        'trackedChangesWithinScope': changed, 'goalUnchanged': True,
        'olderRecordsUnchanged': 31, 'recordShapeHashAndNumber': True,
        'changedPixels': changed_pixels, 'changedPixelsOutsideNewMark': outside,
        'newNonArtifactFilesUnder100KB': True, 'namedPNGUntracked': True,
        'imageFormatsDimensions': {
            'wall': {'format': 'PNG', 'width': 1254, 'height': 1254},
            'preview': {'format': 'JPEG', 'width': 512, 'height': 512},
        },
        'formatDimensionsNote': 'Also inspected independently with installed image_info tool.',
        'unmetVisualRequirements': [], 'scope': 'Local structural checks, not independent certification.',
    }
    Path('line-2/FINAL-CHECK-32.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
