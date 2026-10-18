"""Retain generated pigment only; all ancestral pixels outside the patch stay exact."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('png32', 'gathering/finish_wall.py')
png = importlib.util.module_from_spec(spec)
spec.loader.exec_module(png)
OLD = Path('artifacts/line-2/wall-v11.png')
NEW = Path('artifacts/line-2/wall-v12.png')
RECT = (495, 180, 130, 70)
SOURCE = (140, 225, 735, 340)


def main():
    ancestor = hashlib.sha256(OLD.read_bytes()).hexdigest()
    assert ancestor == 'cb326af3a904ba9e84ee767294016120c304a638880a5208a1b8dbc4a49b1726'
    generated = hashlib.sha256(NEW.read_bytes()).hexdigest()
    width, height, original = png.read_png(OLD)
    dw, dh, draft = png.read_png(NEW)
    assert (width, height) == (1254, 1254)
    assert (dw, dh) == (1024, 1024), 'expected original generated motif; do not run twice'
    final = original[:]
    dx, dy, pw, ph = RECT
    sx, sy, sw, sh = SOURCE
    for y in range(ph):
        ya, yb = sy + y*sh//ph, sy + (y+1)*sh//ph
        for x in range(pw):
            xa, xb = sx + x*sw//pw, sx + (x+1)*sw//pw
            color, selected = [0, 0, 0], 0
            for yy in range(ya, yb):
                for xx in range(xa, xb):
                    pos = (yy*dw+xx)*3
                    r, g, b = draft[pos:pos+3]
                    ochre = r > 65 and r > 1.65*g and r > 2.0*b
                    chalk = 490 < xx < 545 and 485 < yy < 535 and min(r, g, b) > 225
                    if ochre or chalk:
                        selected += 1
                        for c in range(3):
                            color[c] += draft[pos+c]
            if selected:
                alpha = .72 * selected / ((xb-xa)*(yb-ya))
                alpha *= max(0, min(1, x/3, y/3, (pw-1-x)/3, (ph-1-y)/3))
                target = ((dy+y)*width+dx+x)*3
                for c in range(3):
                    final[target+c] = round(original[target+c]*(1-alpha)+color[c]/selected*alpha)
    changed = outside = 0
    for i in range(width*height):
        if final[3*i:3*i+3] != original[3*i:3*i+3]:
            changed += 1
            x, y = i % width, i // width
            outside += not (dx <= x < dx+pw and dy <= y < dy+ph)
    assert outside == 0 and changed > 1000
    digest = png.write_png(NEW, width, height, final)
    continuation = Path('artifacts/line-2/wall.png')
    if continuation.is_symlink():
        continuation.unlink()
    continuation.symlink_to('wall-v12.png')
    rgba = bytearray()
    for y in range(512):
        ya, yb = y*height//512, (y+1)*height//512
        for x in range(512):
            xa, xb = x*width//512, (x+1)*width//512
            count = (yb-ya)*(xb-xa)
            for c in range(3):
                rgba.append(round(sum(final[(yy*width+xx)*3+c]
                                      for yy in range(ya,yb) for xx in range(xa,xb))/count))
            rgba.append(255)
    js = """
const fs = require('fs');
const encode = require('./line-3/tools/corpus-change-receipt/vendor/jpeg-js/lib/encoder.js');
const result = encode({data:fs.readFileSync(0),width:512,height:512},78);
if(result.data.length>100000)throw Error('JPEG too large');
fs.writeFileSync('dist/line-2/32.jpg',result.data);
"""
    subprocess.run(['node','-e',js],input=rgba,check=True)
    report = {
        'round': 32, 'ancestorSha256': ancestor, 'generatedMotifSha256': generated,
        'wallSha256': digest, 'dimensions': [width,height], 'format': 'PNG', 'channels': 'RGB',
        'newMarkRectangle': list(RECT), 'sourceCrop': list(SOURCE),
        'changedPixels': changed, 'changedPixelsOutsideRectangle': outside,
        'method': 'Installed image tool generated flat ochre shelter and chalk dot; '
                  'only isolated pigment was downsampled and blended onto unused ancestral rock.',
        'visualReview': 'Pending final inspection', 'unmetVisualRequirements': [],
        'placementNote': 'The explicitly required beside-record JPEG follows dist/line-2/32.jpg, '
                         'as in ancestor rounds, despite the conflicting blanket picture-location sentence.',
        'images': [],
    }
    for path, kind, size in ((NEW,'PNG',[1254,1254]),(continuation,'PNG',[1254,1254]),
                             (Path('dist/line-2/32.jpg'),'JPEG',[512,512])):
        data = path.read_bytes()
        report['images'].append({'path':str(path),'format':kind,'dimensions':size,
                                 'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    Path('line-2/REVIEW-32.json').write_text(json.dumps(report,indent=2)+'\n')
    traits = [('Cave','Crystal'),('Wall','Line 2'),('Number',32),('Left behind','Anchored Gate'),
              ('Meaning','An ochre shelter guards a pale seed as proof, time and conditions meet.'),
              ('One thing','Verify Ethereum account and storage proofs against trusted state roots')]
    record = {'name':'The Guarded Seed','image':'https://api.imd.fun/artifacts/'+digest,
              'attributes':[{'trait_type':key,'value':value} for key,value in traits]}
    assert not Path('dist/line-2/32.json').exists(), 'do not overwrite a numbered record'
    Path('dist/line-2/32.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
