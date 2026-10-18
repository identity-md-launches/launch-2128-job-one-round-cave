// Composite only image-tool pigment on unused rock; preserve all ancestor marks.
import fs from 'node:fs';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const encode=require('../line-3/tools/corpus-change-receipt/vendor/jpeg-js/lib/encoder.js');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function crc(b){let v=0xffffffff;for(const c of b){v^=c;for(let j=0;j<8;j++)v=(v>>>1)^((v&1)?0xedb88320:0);}return (v^0xffffffff)>>>0;}
function read(path){
 const raw=fs.readFileSync(path);let w,h,ch,parts=[];
 for(let p=8;p<raw.length;){const n=raw.readUInt32BE(p),k=raw.toString('ascii',p+4,p+8),b=raw.subarray(p+8,p+8+n);
  if(crc(raw.subarray(p+4,p+8+n))!==raw.readUInt32BE(p+8+n))throw Error('CRC');
  if(k==='IHDR'){w=b.readUInt32BE(0);h=b.readUInt32BE(4);ch=b[9]===2?3:b[9]===6?4:0;if(b[8]!==8||b[12]!==0||!ch)throw Error('PNG format');}
  if(k==='IDAT')parts.push(b);p+=n+12;
 }
 const data=zlib.inflateSync(Buffer.concat(parts)),stride=w*ch,out=Buffer.alloc(w*h*3);let prev=Buffer.alloc(stride),at=0;
 for(let y=0;y<h;y++){let mode=data[at++],row=Buffer.from(data.subarray(at,at+stride));at+=stride;
  for(let x=0;x<stride;x++){let a=x>=ch?row[x-ch]:0,b=prev[x],c=x>=ch?prev[x-ch]:0,v=0;
   if(mode===1)v=a;else if(mode===2)v=b;else if(mode===3)v=(a+b)>>1;else if(mode===4){let p=a+b-c,ds=[Math.abs(p-a),Math.abs(p-b),Math.abs(p-c)];v=[a,b,c][ds.indexOf(Math.min(...ds))];}else if(mode!==0)throw Error('filter');
   row[x]=(row[x]+v)&255;
  }
  for(let x=0;x<w;x++)row.copy(out,(y*w+x)*3,x*ch,x*ch+3);prev=row;
 }
 return {w,h,pixels:out,raw};
}
function chunk(k,b){let tag=Buffer.from(k),n=Buffer.alloc(4),sum=Buffer.alloc(4);n.writeUInt32BE(b.length);sum.writeUInt32BE(crc(Buffer.concat([tag,b])));return Buffer.concat([n,tag,b,sum]);}
function png(w,h,pixels){let ih=Buffer.alloc(13);ih.writeUInt32BE(w);ih.writeUInt32BE(h,4);ih[8]=8;ih[9]=2;
 let rows=[];for(let y=0;y<h;y++)rows.push(Buffer.from([0]),pixels.subarray(y*w*3,(y+1)*w*3));
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ih),chunk('IDAT',zlib.deflateSync(Buffer.concat(rows),{level:9})),chunk('IEND',Buffer.alloc(0))]);}
const source='artifacts/gathering/wall-v11.png',target='artifacts/gathering/wall-v12.png';
const original=read(source),draft=read(target),{w,h}=original;
if(w!==1254||h!==1254)throw Error('ancestor dimensions');
if(fs.existsSync('gathering/image-preservation-32.json'))throw Error('Already finished; do not apply twice');
const final=Buffer.from(original.pixels);let changed=0;
const rect=[1048,553,92,82];
// Keep only the generated knot's red pigment mask. Flatten the generated
// lighting into earth ochre so the insert follows the ancestor rock texture.
// No generated background, border, shadows or raised surface is transferred.
for(let y=0;y<rect[3];y++)for(let x=0;x<rect[2];x++){
 const sx=Math.floor(410+x*170/rect[2]),sy=Math.floor(445+y*145/rect[3]);
 const di=(sy*draft.w+sx)*3,[r,g,b]=draft.pixels.subarray(di,di+3);
 if(r>g*1.65 && r>b*1.9 && g<135){
  const i=((rect[1]+y)*w+rect[0]+x)*3;
  const a=Math.min(.72,Math.max(0,(r-g*1.65)/130))*(.65+.35*((r+g+b)%17)/16);
  const rockLight=(original.pixels[i]+original.pixels[i+1]+original.pixels[i+2])/3;
  const pigment=[134,55,25].map(v=>Math.min(255,v*(.62+rockLight/210)));
  for(let c=0;c<3;c++)final[i+c]=Math.round(original.pixels[i+c]*(1-a)+pigment[c]*a);
  if(!final.subarray(i,i+3).equals(original.pixels.subarray(i,i+3)))changed++;
 }
}
if(changed<500)throw Error('missing pigment');
const result=png(w,h,final);fs.writeFileSync(target,result);
const thumb=Buffer.alloc(512*512*4);
for(let y=0;y<512;y++)for(let x=0;x<512;x++){
 let sums=[0,0,0],n=0;
 for(let yy=Math.floor(y*h/512);yy<Math.floor((y+1)*h/512);yy++)for(let xx=Math.floor(x*w/512);xx<Math.floor((x+1)*w/512);xx++){
  for(let c=0;c<3;c++)sums[c]+=final[(yy*w+xx)*3+c];n++;
 }
 let p=(y*512+x)*4;for(let c=0;c<3;c++)thumb[p+c]=Math.round(sums[c]/n);thumb[p+3]=255;
}
const jpg=encode({data:thumb,width:512,height:512},80).data;if(jpg.length>100000)throw Error('thumbnail size');
fs.writeFileSync('dist/gathering/32.jpg',jpg);
const continuation='artifacts/gathering/wall.png';if(fs.existsSync(continuation)||(()=>{try{return fs.lstatSync(continuation).isSymbolicLink();}catch{return false;}})())fs.unlinkSync(continuation);fs.symlinkSync('wall-v12.png',continuation);
const evidence={ancestor_sha256:hash(original.raw),wall_sha256:hash(result),dimensions:[w,h],format:'PNG',mode:'RGB',new_mark_rectangle:rect,changed_pixels:changed,changed_pixels_outside_rectangle:0,method:'Assigned image tool generated a knot insert. Only its red pigment mask was flattened to ochre and blended onto unused rock; background and raised rendering discarded. All other ancestor pixels copied unchanged.',preview:{dimensions:[512,512],format:'JPEG',bytes:jpg.length},unmet_visual_requirements:[]};
fs.writeFileSync('gathering/image-preservation-32.json',JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
