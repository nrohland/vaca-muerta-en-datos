import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {validateManifest,validateRelease,validatePair,validateApproval} from './contract.ts';
import {validateOverview} from './delivery.ts';
import {validatePrices} from './metrics.ts';
import type {Bootstrap} from './bootstrap-types.ts';
const hash=(bytes:Uint8Array)=>createHash('sha256').update(bytes).digest('hex');
export async function loadBootstrap(directory=path.join(process.cwd(),'public/data')):Promise<Bootstrap>{
  const read=(name:string)=>readFile(path.join(directory,name));
  const [manifestBytes,full]=await Promise.all([read('manifest.json'),read('release.json')]);
  const manifest=validateManifest(JSON.parse(manifestBytes.toString('utf8')));
  if(hash(full)!==manifest.data_sha256)throw Error('Canonical release hash differs');
  const canonical=validateRelease(JSON.parse(full.toString('utf8')));validatePair(canonical,manifest);
  let release=canonical;
  if(manifest.delivery){
    const ref=manifest.delivery.overview,bytes=await read(ref.path);
    if(bytes.length!==ref.bytes||hash(bytes)!==ref.sha256)throw Error('Overview binding differs');
    const decoded=gunzipSync(bytes,{maxOutputLength:ref.decoded_bytes});
    if(decoded.length!==ref.decoded_bytes)throw Error('Overview decoded size differs');
    release=validateOverview(JSON.parse(decoded.toString('utf8')),manifest,manifest.delivery);
    if(JSON.stringify(release)!==JSON.stringify({...canonical,entities:canonical.entities.filter(r=>r.volume_rank<=5)}))throw Error('Overview differs from canonical release');
  }
  let approval:Bootstrap['data']['approval']=null;
  try{approval=validateApproval(JSON.parse((await read('approval.json')).toString('utf8')),manifest,hash(manifestBytes));}
  catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}
  let prices:Bootstrap['prices']=null,priceError='';
  try{
    const [bytes,bindingBytes]=await Promise.all([read('prices.json'),read('valuation-manifest.json')]);
    const binding=JSON.parse(bindingBytes.toString('utf8'));
    if(binding.schema_version!==1||binding.status!=='candidate'||binding.release_sha256!==manifest.data_sha256||binding.prices_sha256!==hash(bytes))throw Error('Price binding differs');
    prices=validatePrices(JSON.parse(bytes.toString('utf8')));
  }catch{priceError='Referencia de precios no disponible.';}
  return {data:{release,manifest,approval},prices,priceError};
}
