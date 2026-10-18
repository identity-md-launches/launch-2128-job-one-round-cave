/* Export only image-generated pigment; preserve all other ancestor pixels. */
'use strict';
const fs = require('fs');
const zlib = require('zlib');
const crypto = require('crypto');
const assert = require('assert');
const encodeJPEG = require('./tools/corpus-change-receipt/vendor/jpeg-js/lib/encoder.js');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const table = Array.from({length:256}, (_, n) => {
  for (let k=0;k<8;k++) n = (n & 1) ? 0xedb88320 ^ (n >>> 1) : n >>> 1;
  return n >>> 0;
});
function crc32(bytes) {
  let crc=0xffffffff;
  for (const b of bytes) crc=table[(crc ^ b)&255] ^ (crc>>>8);
  return (crc ^ 0xffffffff) >>> 0;
}
function readPNG(bytes) {
  assert(bytes.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex')));
  let width, height, channels;
  const parts=[];
  for (let at=8;at<bytes.length;) {
    const n=bytes.readUInt32BE(at), kind=bytes.toString('ascii',at+4,at+8);
    const body=bytes.subarray(at+8,at+8+n);
    assert.equal(crc32(bytes.subarray(at+4,at+8+n)),bytes.readUInt32BE(at+8+n));
    if (kind==='IHDR') {
      width=body.readUInt32BE(0);height=body.readUInt32BE(4);
      assert.equal(body[8],8);assert([2,6].includes(body[9]));
      assert.equal(body[10]+body[11]+body[12],0);
      channels=body[9]===2?3:4;
    } else if (kind==='IDAT') parts.push(body);
    else if (kind==='IEND') break;
    at+=n+12;
  }
  const stride=width*channels, packed=zlib.inflateSync(Buffer.concat(parts));
  assert.equal(packed.length,height*(stride+1));
  const pixels=Buffer.alloc(width*height*channels);
  for (let y=0;y<height;y++) {
    const filter=packed[y*(stride+1)];assert(filter<=4);
    for (let x=0;x<stride;x++) {
      const at=y*stride+x, left=x>=channels?pixels[at-channels]:0;
      const above=y?pixels[at-stride]:0, diagonal=y&&x>=channels?pixels[at-stride-channels]:0;
      let predictor=0;
      if (filter===1) predictor=left;
      if (filter===2) predictor=above;
      if (filter===3) predictor=(left+above)>>>1;
      if (filter===4) {
        const p=left+above-diagonal,a=Math.abs(p-left),b=Math.abs(p-above),c=Math.abs(p-diagonal);
        predictor=a<=b&&a<=c?left:b<=c?above:diagonal;
      }
      pixels[at]=(packed[y*(stride+1)+x+1]+predictor)&255;
    }
  }
  return {width,height,channels,pixels};
}
function writePNG(width,height,pixels) {
  function chunk(kind,body) {
    const data=Buffer.concat([Buffer.from(kind),body]),head=Buffer.alloc(4),tail=Buffer.alloc(4);
    head.writeUInt32BE(body.length);tail.writeUInt32BE(crc32(data));
    return Buffer.concat([head,data,tail]);
  }
  const header=Buffer.alloc(13);header.writeUInt32BE(width,0);header.writeUInt32BE(height,4);
  header[8]=8;header[9]=2;
  const raw=Buffer.alloc(height*(width*3+1));
  for(let y=0;y<height;y++) pixels.copy(raw,y*(width*3+1)+1,y*width*3,(y+1)*width*3);
  return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),
    chunk('IDAT',zlib.deflateSync(raw,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
function main() {
  const oldBytes=fs.readFileSync('artifacts/line-3/wall-v11.png');
  const draftBytes=fs.readFileSync('artifacts/line-3/wall-v12.png');
  assert.equal(hash(oldBytes),'6d84f9613f13dafbdfd74412e10b7b67d09f0e421b32bc9897f0b00bf19e1581');
  assert(!fs.existsSync('dist/line-3/32.json'));
  assert(!fs.existsSync('dist/line-3/32.jpg'));
  const old=readPNG(oldBytes),draft=readPNG(draftBytes);
  assert.deepEqual([old.width,old.height,old.channels],[1254,1254,3]);
  assert.deepEqual([draft.width,draft.height,draft.channels],[1254,1254,3]);
  assert.notEqual(hash(oldBytes),hash(draftBytes));
  const final=Buffer.from(old.pixels);
  const crop=[721,950,195,97], rect=[650,1006,170,80];
  for(let y=0;y<rect[3];y++) for(let x=0;x<rect[2];x++) {
    const sx=crop[0]+Math.floor(x*crop[2]/rect[2]);
    const sy=crop[1]+Math.floor(y*crop[3]/rect[3]);
    const at=(sy*draft.width+sx)*3;
    const [r,g,b]=draft.pixels.subarray(at,at+3);
    let color;
    if(r>95&&r>g*1.95&&g>b*1.3) color=[145,56,28];
    else if(r>130&&g>75&&r>g*1.4&&g>b*1.65) color=[180,117,43];
    else if(r<78&&g<59&&b<43) color=[42,30,21];
    else continue;
    // Worn gaps preserve actual ancestor stone between generated pigment grains.
    if((x*17+y*29)%13<3) continue;
    const target=((rect[1]+y)*old.width+rect[0]+x)*3;
    for(let c=0;c<3;c++) final[target+c]=Math.round(old.pixels[target+c]*.25+color[c]*.75);
  }
  let changed=0,outside=0;
  for(let i=0;i<old.width*old.height;i++) {
    if(!final.subarray(i*3,i*3+3).equals(old.pixels.subarray(i*3,i*3+3))) {
      changed++;
      const x=i%old.width,y=Math.floor(i/old.width);
      if(x<rect[0]||x>=rect[0]+rect[2]||y<rect[1]||y>=rect[1]+rect[3]) outside++;
    }
  }
  assert(changed>0);assert.equal(outside,0);
  const png=writePNG(old.width,old.height,final);
  assert(readPNG(png).pixels.equals(final));
  const rgba=Buffer.alloc(512*512*4);
  for(let y=0;y<512;y++) for(let x=0;x<512;x++) {
    const xa=Math.floor(x*old.width/512),xb=Math.floor((x+1)*old.width/512);
    const ya=Math.floor(y*old.height/512),yb=Math.floor((y+1)*old.height/512);
    for(let c=0;c<3;c++) {
      let sum=0;
      for(let sy=ya;sy<yb;sy++) for(let sx=xa;sx<xb;sx++) sum+=final[(sy*old.width+sx)*3+c];
      rgba[(y*512+x)*4+c]=Math.round(sum/((xb-xa)*(yb-ya)));
    }
    rgba[(y*512+x)*4+3]=255;
  }
  const jpeg=encodeJPEG({data:rgba,width:512,height:512},77).data;
  assert(jpeg.length<100000);
  fs.writeFileSync('artifacts/line-3/wall-v12.png',png);
  try { fs.unlinkSync('artifacts/line-3/wall.png'); } catch(e) { if(e.code!=='ENOENT') throw e; }
  fs.symlinkSync('wall-v12.png','artifacts/line-3/wall.png');
  fs.writeFileSync('dist/line-3/32.jpg',jpeg,{flag:'wx'});
  const report={wall:'artifacts/line-3/wall-v12.png',format:'PNG',dimensions:[1254,1254],mode:'RGB',
    sha256:hash(png),ancestor_sha256:hash(oldBytes),generated_motif_sha256:hash(draftBytes),
    generated_crop:crop,new_mark_rectangle:rect,changed_pixels:changed,changed_pixels_outside_rectangle:outside,
    thumbnail:{path:'dist/line-3/32.jpg',format:'JPEG',dimensions:[512,512],bytes:jpeg.length},
    visual_review:'pending',unmet_visual_requirements:[]};
  fs.writeFileSync('line-3/IMAGE-32.json',JSON.stringify(report,null,2)+'\n');
  const record={name:'The Counted Evidence',image:'https://api.imd.fun/artifacts/'+hash(png),
    attributes:[['Cave','Crystal'],['Wall','Line 3'],['Number',32],['Left behind','Citation Ledger'],
      ['Meaning','Stones gathered in an ochre loop mark citations checked together before they are carried onward.'],
      ['One thing','Offline document search with exact source line citations']].map(([trait_type,value])=>({trait_type,value}))};
  fs.writeFileSync('dist/line-3/32.json',JSON.stringify(record,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify(report,null,2));
}
if(require.main===module) main();
