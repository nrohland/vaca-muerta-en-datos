import {test} from "node:test";
import assert from "node:assert/strict";
import {chartVisibility} from "../lib/chart-visibility.ts";
test("hiding verified USD by choice does not claim missing prices",()=>{
  const result=chartVisibility({wells:false,fluid:"oil",detailView:true,selected:"physical",hasEstimated:true});
  assert.equal(result.showPhysical,true);assert.equal(result.monetary,false);assert.equal(result.unavailable,false);
});
test("a selected USD series falls back to physical when the window has no valid prices",()=>{
  const result=chartVisibility({wells:false,fluid:"oil",detailView:true,selected:"value",hasEstimated:false});
  assert.equal(result.showPhysical,true);assert.equal(result.monetary,false);assert.equal(result.unavailable,true);assert.equal(result.activeSeries,"physical");
});
test("productive wells retain physical charts; gas reference can show USD",()=>{
  for(const options of [{wells:true,fluid:"oil" as const}]){
    const result=chartVisibility({...options,detailView:true,selected:"value",hasEstimated:true});
    assert.equal(result.showPhysical,true);assert.equal(result.monetary,false);
    assert.equal(result.unavailable,!options.wells);
  }
});
test("available USD can be isolated while overview preserves both series",()=>{
  const options={wells:false,fluid:"oil" as const,selected:"value" as const,hasEstimated:true};
  assert.equal(chartVisibility({...options,detailView:true}).showPhysical,false);
  const overview=chartVisibility({...options,detailView:false});
  assert.equal(overview.showPhysical,true);assert.equal(overview.monetary,true);
});
