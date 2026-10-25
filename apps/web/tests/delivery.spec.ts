import {test,expect} from './browser-fixtures';
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import path from 'node:path';
const base='/vaca-muerta-pulse/';
const evidence=process.env.EVIDENCE_DIR??path.resolve('test-results/delivery');
for(const mobile of [false,true])test(`delivery budgets, all views, fluid switches and deep links ${mobile?'mobile':'desktop'}`,async({page})=>{
 await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000});
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 await page.addInitScript(()=>{(window as any).__longTasks=[];try{new PerformanceObserver(list=>{(window as any).__longTasks.push(...list.getEntries().map(e=>e.duration));}).observe({entryTypes:['longtask']});}catch{}});
 const start=Date.now();await page.goto(base);await expect(page.locator('.kpi-card--primary')).toBeVisible();
 const ready=Date.now()-start;
 expect(requests.some(url=>url.endsWith('/data/release.json'))).toBe(false);
 expect(requests.filter(url=>/\/(oil|gas)-(company|area)-/.test(url))).toHaveLength(0);
 const resources=await page.evaluate(()=>performance.getEntriesByType('resource').map(e=>({name:e.name,transfer:(e as PerformanceResourceTiming).transferSize,encoded:(e as PerformanceResourceTiming).encodedBodySize})));
 expect(resources.some(r=>r.name.includes('/overview-'))).toBe(false);
 mkdirSync(evidence,{recursive:true});
 await page.waitForTimeout(1600); // Let chart animations finish for representative captures.
 await page.screenshot({animations:'disabled',path:path.join(evidence,`summary-${mobile?'mobile':'desktop'}.png`),fullPage:mobile});
 for(const [label,selector] of [['Producción','.production-dashboard'],['Operadores','.operators-dashboard'],['Áreas','.areas-dashboard'],['Actividad','.activity-dashboard']] as const){
  await page.getByRole('tab',{name:label,exact:true}).click();await expect(page.locator(selector)).toBeVisible();
  await page.waitForTimeout(1600); // Let chart animations finish for representative captures.
 await page.screenshot({animations:'disabled',path:path.join(evidence,`${label}-${mobile?'mobile':'desktop'}.png`),fullPage:mobile});
 }
 await page.getByRole('tab',{name:'Operadores',exact:true}).click();await expect(page.locator('.operators-dashboard')).toBeVisible();
 const before=requests.filter(url=>/\/oil-company-/.test(url)).length;
 await page.getByRole('tab',{name:'Resumen',exact:true}).click();await page.getByRole('tab',{name:'Operadores',exact:true}).click();await expect(page.locator('.operators-dashboard')).toBeVisible();
 expect(requests.filter(url=>/\/oil-company-/.test(url))).toHaveLength(before);
 await page.getByRole('button',{name:'Gas',exact:true}).click();await expect(page.locator('.operators-dashboard')).toBeVisible();
 expect(requests.some(url=>/\/gas-company-/.test(url))).toBe(true);
 await page.goto(base+'?tab=areas&fluid=gas');await expect(page.locator('.areas-dashboard')).toBeVisible();
 await expect(page.getByRole('button',{name:'Gas',exact:true})).toHaveAttribute('aria-pressed','true');
 writeFileSync(path.join(evidence,`delivery-${mobile?'mobile':'desktop'}.json`),JSON.stringify({ready_ms:ready,resources,requests,long_tasks_ms:await page.evaluate(()=>(window as any).__longTasks),scope:'Local static browser test; no deployed field Core Web Vitals claim'},null,2));
});
test('broken detail stays unavailable and retry preserves context without reloading verified overview',async({page})=>{
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
 await page.route('**/data/snapshots/**/oil-area-*.json.gz',route=>route.fulfill({status:503}));
 await page.goto(base+'?tab=areas&fluid=oil');await expect(page.locator('#main').getByRole('alert')).toBeVisible();await expect(page.locator('.areas-dashboard')).toHaveCount(0);
 await page.unroute('**/data/snapshots/**/oil-area-*.json.gz');const manifestCount=requests.filter(u=>u.endsWith('/data/manifest.json')).length;
 await page.getByRole('button',{name:'Reintentar',exact:true}).click();await expect(page.locator('.areas-dashboard')).toBeVisible();
 expect(requests.filter(u=>u.endsWith('/data/manifest.json'))).toHaveLength(manifestCount);
 await expect(page.getByRole('tab',{name:'Áreas',exact:true})).toHaveAttribute('aria-selected','true');
});

test('selecting an active filter does not add duplicate history entries',async({page})=>{
 await page.goto(base);await expect(page.locator('.kpi-card--primary')).toBeVisible();
 const before=await page.evaluate(()=>history.length);
 await page.getByRole('button',{name:'Petróleo',exact:true}).click();
 await page.getByRole('tab',{name:'Resumen',exact:true}).click();
 expect(await page.evaluate(()=>history.length)).toBe(before);
});

test('initial summary is present in HTML without client JavaScript',async({browser})=>{
 const context=await browser.newContext({javaScriptEnabled:false});
 try{
  const page=await context.newPage();await page.goto(base);
  await expect(page.locator('.kpi-card--primary')).toBeVisible();
  await expect(page.locator('#main')).not.toContainText('Cargando agregados oficiales');
 }finally{await context.close();}
});
test('rapid tab round-trip reuses an in-flight public detail shard',async({page})=>{
 let count=0,unblock!:()=>void;const gate=new Promise<void>(resolve=>{unblock=resolve;});
 await page.route('**/data/snapshots/**/oil-company-*.json.gz',async route=>{count++;await gate;await route.continue();});
 try{
  await page.goto(base+'?tab=operators&fluid=oil');await expect.poll(()=>count).toBe(1);
  await page.getByRole('tab',{name:'Resumen',exact:true}).click();await expect(page.locator('.kpi-card--primary')).toBeVisible();
  await page.getByRole('tab',{name:'Operadores',exact:true}).click();
 }finally{unblock();}
 await expect(page.locator('.operators-dashboard')).toBeVisible();expect(count).toBe(1);
});
