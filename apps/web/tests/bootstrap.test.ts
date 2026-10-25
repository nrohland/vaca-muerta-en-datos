import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,writeFile,rm} from 'node:fs/promises';
import path from 'node:path';
import {tmpdir} from 'node:os';
import {loadBootstrap} from '../lib/bootstrap.server.ts';
test('build bootstrap retains candidate state, validates overview and prices',async()=>{
 const result=await loadBootstrap();
 assert.equal(result.data.manifest.source.approved_period,'2026-08-01');
 assert.equal(result.data.approval,null);
 assert.equal(result.data.release.entities.length,880);
 assert.ok(result.prices);
});
test('invalid canonical bytes fail build before any metric is rendered',async()=>{
 const directory=await mkdtemp(path.join(tmpdir(),'vm-bootstrap-'));
 try{
  await cp('public/data',directory,{recursive:true});
  const file=path.join(directory,'release.json');await writeFile(file,(await readFile(file,'utf8'))+' ');
  await assert.rejects(loadBootstrap(directory),/Canonical release hash differs/);
 }finally{await rm(directory,{recursive:true,force:true});}
});
test('invalid approval blocks the build; absent approval stays preliminary',async()=>{
 const directory=await mkdtemp(path.join(tmpdir(),'vm-approval-'));
 try{
  await cp('public/data',directory,{recursive:true});
  await writeFile(path.join(directory,'approval.json'),JSON.stringify({status:'approved',version:'wrong'}));
  await assert.rejects(loadBootstrap(directory),/Aprobación no corresponde/);
 }finally{await rm(directory,{recursive:true,force:true});}
});
test('missing auxiliary prices preserve validated warehouse values',async()=>{
 const directory=await mkdtemp(path.join(tmpdir(),'vm-prices-'));
 try{
  await cp('public/data',directory,{recursive:true});await rm(path.join(directory,'prices.json'));
  const result=await loadBootstrap(directory);
  assert.equal(result.prices,null);assert.ok(result.priceError);
  assert.ok(result.data.release.production.some(row=>typeof row.estimated_value_usd==='number'));
 }finally{await rm(directory,{recursive:true,force:true});}
});
