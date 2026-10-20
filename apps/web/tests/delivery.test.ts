import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {buildDelivery} from '../scripts/build_delivery.mjs';
import {validateDelivery,validateEntities,validateOverview,readDelivery,createRequestCache} from '../lib/delivery.ts';
import {validateManifest} from '../lib/contract.ts';
test('derived delivery preserves complete canonical metrics and defers only entity detail',()=>{
 const directory=mkdtempSync(path.join(tmpdir(),'vm-delivery-'));
 try{
  for(const f of ['release.json','manifest.json'])copyFileSync(path.join('public/data',f),path.join(directory,f));
  const bytes=readFileSync(path.join(directory,'release.json')),full=JSON.parse(bytes.toString());
  const d=validateDelivery(buildDelivery(directory),createHash('sha256').update(bytes).digest('hex')),manifest=validateManifest(JSON.parse(readFileSync(path.join(directory,'manifest.json'),'utf8')));
  assert.ok(d.overview.bytes<=250*1024);assert.equal(d.release_sha256,createHash('sha256').update(bytes).digest('hex'));
  const read=(r:any)=>{const b=readFileSync(path.join(directory,r.path));assert.equal(b.length,r.bytes);assert.equal(createHash('sha256').update(b).digest('hex'),r.sha256);return JSON.parse(gunzipSync(b).toString());};
  const overview=validateOverview(read(d.overview),manifest,d);assert.deepEqual(overview.production,full.production);
  const entities:any[]=[];
  for(const f of ['oil','gas'] as const)for(const dimension of ['company','area'] as const){const ref=d.entities[`${f}-${dimension}`];entities.push(...validateEntities(read(ref),overview,ref,f,dimension));}
  const key=(r:any)=>`${r.fluid}/${r.dimension}/${r.entity_id}/${r.periodo}`;
  assert.deepEqual(entities.sort((a,b)=>key(a).localeCompare(key(b))),full.entities.sort((a:any,b:any)=>key(a).localeCompare(key(b))));
  const mb=readFileSync(path.join(directory,'manifest.json'));buildDelivery(directory);assert.deepEqual(readFileSync(path.join(directory,'manifest.json')),mb);assert.deepEqual(readFileSync(path.join(directory,'release.json')),bytes);
  assert.throws(()=>validateDelivery({...d,release_sha256:'0'.repeat(64)},d.release_sha256));
  assert.throws(()=>validateDelivery({...d,overview:{...d.overview,path:'../other.json.gz'}},d.release_sha256));
  const modified=read(d.entities['oil-company']);modified.find((r:any)=>r.volume_rank<=5).volume++;
  assert.throws(()=>validateEntities(modified,overview,d.entities['oil-company'],'oil','company'));
  writeFileSync(path.join(directory,'approval.json'),'{}');
  const m=JSON.parse(mb.toString());delete m.delivery;writeFileSync(path.join(directory,'manifest.json'),JSON.stringify(m));assert.throws(()=>buildDelivery(directory),/approved/);
 }finally{rmSync(directory,{recursive:true,force:true});}
});
test('browser delivery rejects tampered and oversized bodies before parsing',async()=>{
 const d=validateManifest(JSON.parse(readFileSync('public/data/manifest.json','utf8'))).delivery!;
 const old=globalThis.fetch;try{
  globalThis.fetch=async()=>new Response(new Uint8Array(d.overview.bytes+1));await assert.rejects(readDelivery(d.overview,''),/Tamaño/);
  globalThis.fetch=async()=>new Response(new Uint8Array(d.overview.bytes));await assert.rejects(readDelivery(d.overview,''),/manifiesto/);
 }finally{globalThis.fetch=old;}
});

test('public shard cache shares in-flight/completed reads, isolates release keys and allows retries',async()=>{
 const cache=createRequestCache<number>();let calls=0,complete!:(v:number)=>void;
 const loader=()=>{calls++;return new Promise<number>(resolve=>{complete=resolve;});};
 const first=cache.read('release-a/oil-area',loader),second=cache.read('release-a/oil-area',loader);
 assert.equal(first,second);await Promise.resolve();assert.equal(calls,1);complete(42);assert.equal(await first,42);
 assert.equal(await cache.read('release-a/oil-area',async()=>{throw Error('duplicate');}),42);
 assert.equal(await cache.read('release-b/oil-area',async()=>84),84);
 await assert.rejects(cache.read('release-a/gas-area',async()=>{throw Error('offline');}));
 assert.equal(await cache.read('release-a/gas-area',async()=>21),21);
});
