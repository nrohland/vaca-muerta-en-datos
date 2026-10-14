// Deterministic candidate assets. Canonical snapshot remains intact; no approval generation.
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateRelease,validateManifest,validatePair} from '../lib/contract.ts';
import {validateDelivery} from '../lib/delivery.ts';
export function buildDelivery(directory){
 const full=readFileSync(path.join(directory,'release.json')),mb=readFileSync(path.join(directory,'manifest.json'));
 const hash=b=>createHash('sha256').update(b).digest('hex');
 const release=validateRelease(JSON.parse(full)),manifest=validateManifest(JSON.parse(mb));validatePair(release,manifest);
 if(hash(full)!==manifest.data_sha256)throw Error('Canonical release hash differs');
 const assets=new Map();
 function asset(key,value,rows){const plain=Buffer.from(JSON.stringify(value)),compressed=gzipSync(plain,{level:9}),sha=hash(compressed);const ref={path:`snapshots/${manifest.data_sha256}/${key}-${sha.slice(0,16)}.json.gz`,sha256:sha,bytes:compressed.length,decoded_bytes:plain.length,rows};assets.set(ref.path,compressed);return ref;}
 const delivery={schema_version:1,release_sha256:manifest.data_sha256,overview:asset('overview',{...release,entities:release.entities.filter(r=>r.volume_rank<=5)},release.entities.filter(r=>r.volume_rank<=5).length),entities:{}};
 for(const f of ['oil','gas'])for(const d of ['company','area']){const rows=release.entities.filter(r=>r.fluid===f&&r.dimension===d);delivery.entities[`${f}-${d}`]=asset(`${f}-${d}`,rows,rows.length);}
 validateDelivery(delivery,manifest.data_sha256);
 if(delivery.overview.bytes>250*1024)throw Error('Overview exceeds 250 KiB compressed budget');
 const changed=JSON.stringify(manifest.delivery)!==JSON.stringify(delivery);
 if(changed&&existsSync(path.join(directory,'approval.json')))throw Error('Refusing to change an approved manifest; explicit new candidate required');
 for(const [name,bytes] of assets){const dest=path.join(directory,name);mkdirSync(path.dirname(dest),{recursive:true});writeFileSync(dest,bytes);}
 if(changed)writeFileSync(path.join(directory,'manifest.json'),JSON.stringify({...manifest,delivery},null,2)+'\n');
 return delivery;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const index=process.argv.indexOf('--data-dir');const directory=index<0?path.resolve('public/data'):path.resolve(process.argv[index+1]);
 const d=buildDelivery(directory);console.log(JSON.stringify({status:'pass',overview_bytes:d.overview.bytes,canonical_release_unchanged:true,shards:Object.keys(d.entities).length}));
}
