import {test} from 'node:test';
import assert from 'node:assert/strict';
import {kpiParts, trendClass, kpiState} from '../lib/presentation.ts';
test('compact numbers preserve ES/EN numeric strings and separate scale from units',()=>{
 for(const [input,unit,expected] of [
  ['20,76 M','bbl',{value:'20,76',unit:'M bbl'}],
  ['20.76M','bbl',{value:'20.76',unit:'M bbl'}],
  ['−4,4 M USD',undefined,{value:'−4,4',unit:'M USD'}],
  ['+12.5%',undefined,{value:'+12.5',unit:'%'}],
  ['2.959,0','MMm³',{value:'2.959,0',unit:'MMm³'}],
  ['No disponible',undefined,{value:'No disponible',unit:undefined}],
 ] as const) assert.deepEqual(kpiParts(input,unit),expected);
});
test('changes have shared positive negative and missing semantics',()=>{
 for(const value of [null,undefined,NaN,Infinity,0]) {assert.equal(trendClass(value),'trend-neutral');assert.equal(kpiState(value),'neutral');}
 assert.equal(trendClass(1),'trend-positive');assert.equal(kpiState(-1),'unfavorable');
 assert.equal(trendClass(-1),'trend-negative');assert.equal(kpiState(1),'favorable');
});
