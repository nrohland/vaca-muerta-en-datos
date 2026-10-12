import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validateRelease, type Row} from "../lib/contract.ts";
import {activityPoints, activityKpis, averagePerProductiveWell, activityCsv} from "../lib/activity-analysis.ts";
import {daysInMonth, shiftMonth} from "../lib/metrics.ts";
const rows = validateRelease(JSON.parse(readFileSync(new URL("../public/data/release.json",import.meta.url),"utf8"))).production;
test("real mart unique well counts, exact calendar differences and physical averages for both fluids",()=>{
  for(const current of rows){
    const point=activityPoints(rows,current.fluid,current.periodo,1)[0];
    assert.equal(point.wells,current.positive_producing_wells);
    assert.equal(point.average,current.volume*(current.fluid==='gas'?1e6:1)/daysInMonth(current.periodo)/current.positive_producing_wells);
    for(const comparison of ['mom','yoy'] as const){
      const base=rows.find(r=>r.fluid===current.fluid&&r.periodo===shiftMonth(current.periodo,comparison==='mom'?-1:-12));
      assert.equal(point[comparison],base?current.positive_producing_wells-base.positive_producing_wells:null);
      assert.equal(activityKpis(rows,current,comparison).delta,point[comparison]);
    }
  }
});
test("missing calendar months remain null, never compare with nearest observation or other fluid",()=>{
  const selected=rows.filter(r=>r.fluid==='oil').slice(-3);
  const sparse=[selected[0],selected[2],...rows.filter(r=>r.fluid==='gas')];
  const points=activityPoints(sparse,'oil',selected[2].periodo,3);
  assert.equal(points[1].wells,null);assert.equal(points[1].average,null);assert.equal(points[1].mom,null);assert.equal(points[2].mom,null);
});
test("zero count has no average but remains a valid absolute difference base; leap month uses calendar days",()=>{
 const original=rows.find(r=>r.fluid==='oil')!;
 const base={...original,periodo:'2024-02-01',volume:0,positive_producing_wells:0};
 const current={...original,periodo:'2024-03-01',volume:310,positive_producing_wells:10};
 assert.equal(averagePerProductiveWell(base),null);
 assert.equal(activityKpis([base,current],current,'mom').delta,10);
 assert.equal(activityKpis([base,current],current,'mom').pct,null);
 assert.equal(averagePerProductiveWell({...base,volume:290,positive_producing_wells:10}),1);
});
test("selected history never includes future data and CSV retains null gaps and exact raw values",()=>{
 const current=rows.find(r=>r.fluid==='gas'&&r.periodo==='2025-02-01')!;
 const points=activityPoints(rows,'gas',current.periodo,12);
 assert.equal(points.length,12);assert.ok(points.every(p=>p.periodo<=current.periodo));
 const csv=activityCsv(points,'gas');assert.ok(csv.startsWith('periodo,positive_producing_wells,m3_per_productive_well_calendar_day'));
 assert.ok(csv.includes(String(points.at(-1)!.average)));
 const empty=activityCsv([{periodo:'2024-01-01',wells:null,average:null,mom:null,yoy:null,momBase:'2023-12-01',yoyBase:'2023-01-01'}],'oil');
 assert.ok(empty.includes('2024-01-01,,,,2023-12-01,,2023-01-01'));
});
