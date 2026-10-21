// CPU microbenchmark over the bundled public snapshot; not field Web Vitals or a timing assertion.
// Run: node --experimental-strip-types scripts/benchmark_analysis.mjs
import {readFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import {areaRanking} from '../lib/area-analysis.ts';
import {formatters} from '../lib/i18n.ts';
const release=JSON.parse(readFileSync(new URL('../public/data/release.json',import.meta.url),'utf8'));
const current=release.production.at(-1);
const start=performance.now();
for(let i=0;i<300;i++)areaRanking(release.entities,current,null,'volume','yoy');
const ranking=performance.now()-start,formatter=formatters('es'),second=performance.now();
for(let i=0;i<10000;i++){formatter.number(123456.789,2);formatter.month('2026-08-01');}
console.log(JSON.stringify({area_ranking_300_ms:ranking,number_and_month_10000_ms:performance.now()-second,scope:'Single local CPU sample; variable by host/load; not browser timings or an SLA'},null,2));
