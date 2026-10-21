import {test} from 'node:test';
import assert from 'node:assert/strict';
import {bubbleRadius,mapValue} from '../lib/map-analysis.ts';
test('circle area, not radius, is proportional to volume with no hidden minimum',()=>{
 const maximum=10000;
 for(const value of [1,10,100,2500,10000])assert.ok(Math.abs((bubbleRadius(value,maximum)/bubbleRadius(maximum,maximum))**2-value/maximum)<1e-12);
 assert.equal(bubbleRadius(null,maximum),0);assert.equal(bubbleRadius(0,maximum),0);assert.equal(bubbleRadius(10,0),0);
});
test('a structural missing row is unavailable, not observed zero',()=>{
 const entry={value:0,entity:{is_absent_current:false,reported_well_rows:1}} as any;
 assert.equal(mapValue(entry),0);
 assert.equal(mapValue({...entry,entity:{...entry.entity,is_absent_current:true}}),null);
 assert.equal(mapValue({...entry,entity:{...entry.entity,reported_well_rows:0}}),null);
 assert.equal(mapValue(undefined),null);
});
