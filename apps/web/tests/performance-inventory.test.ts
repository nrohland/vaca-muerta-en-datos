import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';

test('build budget counts mixed-case script tags and excludes legacy nomodule assets',()=>{
 const dir=mkdtempSync(path.join(tmpdir(),'vm-budget-'));
 try{
  mkdirSync(path.join(dir,'out/_next'),{recursive:true});
  writeFileSync(path.join(dir,'out/_next/a.js'),'a();');
  writeFileSync(path.join(dir,'out/_next/b.js'),'bb();');
  writeFileSync(path.join(dir,'out/index.html'),'<SCRIPT SRC="/_next/a.js"></SCRIPT><script src="/_next/b.js"></script><script NOMODULE src="/_next/missing.js"></script>');
  execFileSync(process.execPath,[path.resolve('scripts/check_performance.mjs')],{cwd:dir,env:{...process.env,NEXT_PUBLIC_BASE_PATH:''}});
  const report=JSON.parse(readFileSync(path.join(dir,'out/performance-budget.json'),'utf8'));
  assert.equal(report.modern_initial_js_bytes,9);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

test('serialized HTML cannot bypass the transfer budget',()=>{
 const dir=mkdtempSync(path.join(tmpdir(),'vm-html-budget-'));
 try{
  mkdirSync(path.join(dir,'out'),{recursive:true});
  // Deterministic pseudo-random text avoids a trivially compressible fixture.
  let state=13;const chars=[];
  for(let i=0;i<600000;i++){state=(Math.imul(state,1664525)+1013904223)>>>0;chars.push(String.fromCharCode(33+(state>>>24)%90));}
  writeFileSync(path.join(dir,'out/index.html'),chars.join(''));
  assert.throws(()=>execFileSync(process.execPath,[path.resolve('scripts/check_performance.mjs')],{cwd:dir,env:{...process.env,NEXT_PUBLIC_BASE_PATH:''},stdio:'pipe'}),/Command failed/);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
