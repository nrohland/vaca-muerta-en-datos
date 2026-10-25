import {readFileSync,writeFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import path from 'node:path';
const html=readFileSync('out/index.html','utf8');
const base=process.env.NEXT_PUBLIC_BASE_PATH??'/vaca-muerta-pulse';
const paths=new Set([...html.matchAll(/<script\b[^>]*>/gi)].map(m=>m[0]).filter(t=>!/nomodule/i.test(t)).map(t=>t.match(/\bsrc="([^"]+)"/i)?.[1]).filter(Boolean));
let bytes=0,gzip=0;
for(const url of paths){const relative=url.slice(base.length);if(!url.startsWith(base+'/_next/'))throw Error('Unexpected script asset');const b=readFileSync(path.join('out',relative));bytes+=b.length;gzip+=gzipSync(b,{level:9}).length;}
if(gzip>200*1024)throw Error('Initial JavaScript exceeds 200 KiB gzip budget');
const htmlGzip=gzipSync(Buffer.from(html),{level:9}).length;
if(htmlGzip>300*1024)throw Error('Initial HTML exceeds 300 KiB gzip budget');
if(htmlGzip+gzip>450*1024)throw Error('HTML plus initial JavaScript exceeds 450 KiB gzip budget');
const report={html_bytes:Buffer.byteLength(html),html_gzip_bytes:htmlGzip,html_gzip_budget:300*1024,html_and_initial_js_gzip_bytes:htmlGzip+gzip,combined_gzip_budget:450*1024,status:'pass',modern_initial_js_bytes:bytes,modern_initial_js_gzip_bytes:gzip,gzip_budget:200*1024,scope:'HTML and initial script asset gzip sizes; excludes CSS, dynamic chunks and field Web Vitals'};
writeFileSync('out/performance-budget.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
