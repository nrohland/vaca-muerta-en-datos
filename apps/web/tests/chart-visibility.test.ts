import {test} from "node:test";
import assert from "node:assert/strict";
import {chartVisibility} from "../lib/chart-visibility.ts";
const common={wells:false,fluid:"oil" as const,hasEstimated:true,mode:"volume" as const};
test("overview follows volume/value mode with exactly one visible magnitude",()=>{
  for(const mode of ["volume","value"] as const){
    const result=chartVisibility({...common,mode,detailView:false,selected:"physical"});
    assert.equal(result.showPhysical,mode==="volume");
    assert.equal(result.monetary,mode==="value");
    assert.equal(result.unavailable,false);
  }
});
test("hiding verified USD by choice does not claim missing prices",()=>{
 const result=chartVisibility({...common,detailView:true,selected:"physical"});
 assert.equal(result.showPhysical,true);assert.equal(result.monetary,false);assert.equal(result.unavailable,false);
});
test("unavailable USD falls back to physical without inventing zeros",()=>{
 const result=chartVisibility({...common,detailView:true,selected:"value",hasEstimated:false});
 assert.equal(result.activeSeries,"physical");assert.equal(result.unavailable,true);
});
test("productive wells never acquire a monetary axis",()=>{
 const result=chartVisibility({...common,wells:true,mode:"value",detailView:false,selected:"value"});
 assert.equal(result.showPhysical,true);assert.equal(result.monetary,false);assert.equal(result.unavailable,false);
});
test("detail series choice stays independent of global metric until changed",()=>{
 const result=chartVisibility({...common,detailView:true,selected:"value"});
 assert.equal(result.showPhysical,false);assert.equal(result.monetary,true);
});
