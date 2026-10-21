// Run from apps/web. Originals/provenance are preserved; derivatives cover 4x a 36px slot.
const sharp=require('sharp');
const fs=require('node:fs/promises');
const crypto=require('node:crypto');
(async()=>{
 const rows=[];
 for(const id of ['SHE','TPT']){
  const src=`public/operators/${id}.jpg`,out=`public/operators/${id}.webp`;
  const original=await fs.readFile(src);
  const reference=await sharp(original).resize({width:144,height:144,fit:'inside',withoutEnlargement:true}).png().toBuffer();
  const webp=await sharp(reference).webp({lossless:true,effort:6}).toBuffer();
  const a=await sharp(reference).ensureAlpha().raw().toBuffer(),b=await sharp(webp).ensureAlpha().raw().toBuffer();
  if(!a.equals(b))throw Error('Derivative pixel verification failed');
  await fs.writeFile(out,webp);
  rows.push({id,original:`${id}.jpg`,file:`${id}.webp`,max_dimension:144,original_bytes:original.length,bytes:webp.length,source_sha256:crypto.createHash('sha256').update(original).digest('hex'),sha256:crypto.createHash('sha256').update(webp).digest('hex'),encoding:'lossless_after_resize'});
 }
 await fs.writeFile('public/operators/optimized.json',JSON.stringify(rows,null,2)+'\n');
 console.log(rows.map(r=>({id:r.id,before:r.original_bytes,after:r.bytes})));
})();
