import {test,expect} from './browser-fixtures';
const base='/vaca-muerta-pulse/?month=2026-08-01&fluid=gas&comparison=yoy';
test('gas reference methodology lives behind its KPI and notation uses a smaller unit',async({page})=>{
 await page.goto(base);await expect(page.locator('#panel-summary .kpi-card')).toHaveCount(4);
 await expect(page.locator('#panel-summary > .availability-note')).toHaveCount(0);
 const card=page.locator('#panel-summary .kpi-card').nth(3);
 await card.getByRole('button',{name:/Metodología/}).click();
 await expect(card.locator('.kpi-back')).toContainText('1.036 BTU/pie³');
 await expect(card.locator('.kpi-back')).toContainText('No representa facturación efectiva');
 await page.getByRole('tab',{name:'Producción',exact:true}).click();
 await page.getByRole('button',{name:'Petróleo',exact:true}).click();
 const metric=page.locator('.production-dashboard .kpi-card--primary .kpi-value');
 await expect(metric.locator('.kpi-unit')).toContainText('M bbl');
 expect(await metric.evaluate(e=>parseFloat(getComputedStyle(e.querySelector('.kpi-unit')!).fontSize)<parseFloat(getComputedStyle(e).fontSize))).toBe(true);
});
test('official area geometry supports selection and shares global filters',async({page})=>{
 const worker=page.waitForResponse(response=>/\/_next\/static\/media\/.*\.mjs$/.test(new URL(response.url()).pathname));
 await page.goto(base+'&tab=areas');const polygons=page.locator('.area-bubble');await expect(polygons).toHaveCount(68);
 expect((await worker).ok()).toBe(true);
 await expect(page.locator('.area-map-card')).toContainText('68 con geometría');
 await page.locator('.area-bubble[data-area="AFED"]').focus();await expect(page.locator('.map-readout')).toContainText('AGUADA FEDERAL');
 await page.locator('.area-bubble[data-area="AFED"]').press('Enter');await expect(page).toHaveURL(/area=AFED/);
 await expect(page.locator('.areas-detail-heading h2')).toContainText('AGUADA FEDERAL');
 await page.getByRole('button',{name:'Valor USD',exact:true}).click();await expect(page.locator('.area-map-card')).toContainText('USD');
 await page.getByRole('button',{name:'English',exact:true}).click();await expect(page.locator('.area-map-card h2')).toContainText('Where production');
 await page.reload();await expect(polygons).toHaveCount(68);await expect(page).toHaveURL(/area=AFED/);
});
test('activity exposes meaningful comparisons and expands the full table',async({page})=>{
 await page.goto(base+'&tab=activity');await expect(page.locator('.activity-count-plot .recharts-bar')).toHaveCount(1);
 await expect(page.locator('.activity-average-plot .recharts-area')).toHaveCount(1);
 await expect(page.locator('.activity-average-current')).toHaveCount(1);
 await expect(page.locator('.activity-data .trend-positive').first()).toContainText('+');
 await page.getByRole('button',{name:'Expandir tabla',exact:true}).click();await expect(page.locator('.activity-table-scroll')).toHaveClass(/is-expanded/);
 await page.getByLabel('Mes de producción').selectOption('2023-01-01');await expect(page.locator('.activity-average-current')).toHaveCount(1);
 await expect(page.locator('.activity-dashboard')).toContainText('Sin promedio válido para el mes base');
});
test('map and all detail views stay within a narrow English dark viewport',async({page})=>{
 await page.setViewportSize({width:320,height:812});await page.goto(base+'&tab=areas');
 await expect(page.getByRole('button',{name:'Argentina',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'English',exact:true}).click();await page.getByRole('button',{name:'Dark mode',exact:true}).click();
 for(const name of ['Areas','Activity','Production','Operators','Overview']){
  await page.getByRole('tab',{name,exact:true}).click();
  await expect(page.getByRole('tabpanel')).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
});
test('desktop explorers align panels and keep scrolling inside their rankings',async({page})=>{
 for(const height of [704,900]){
  await page.setViewportSize({width:1440,height});
  for(const tab of ['operators','areas']){
   await page.goto(base.replace('fluid=gas','fluid=oil')+'&tab='+tab);
   const left=page.locator(tab==='operators'?'.operators-ranking':'.area-map-card');
   const right=page.locator(tab==='operators'?'.operators-evolution':'.areas-ranking');
   await expect(left).toBeVisible();await expect(right).toBeVisible();
   await expect.poll(async()=>Math.abs((await left.boundingBox())!.height-(await right.boundingBox())!.height)).toBeLessThan(2);
   const list=page.locator(tab==='operators'?'.operators-ranking-list':'.areas-ranking .ranking-list');
   await expect.poll(()=>list.evaluate(e=>e.scrollHeight>e.clientHeight)).toBe(true);
   await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+2),{message:`${tab} at 1440×${height} fits the viewport`}).toBe(true);
  }
 }
});
test('overlapping map symbols offer explicit selection and keep selected readout coherent',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto(base.replace('fluid=gas','fluid=oil')+'&tab=areas');
 const loma=page.locator('.area-bubble[data-area="LCAM"]');await expect(loma).toBeVisible();
 await loma.scrollIntoViewIfNeeded();await loma.click({force:true});
 await expect(page.locator('.map-choice')).toBeVisible();
 await page.locator('.map-choice').getByRole('button',{name:/^LOMA CAMPANA/}).click();
 await expect(page).toHaveURL(/area=LCAM/);
 await expect(page.locator('.map-readout strong')).toHaveText('LOMA CAMPANA');
 await expect(page.locator('.areas-detail-heading h2')).toHaveText('LOMA CAMPANA');
 await page.locator('.area-bubble[data-area="BNDS"]').focus();
 await expect(page.locator('.map-readout strong')).toHaveText('LOMA CAMPANA');
 await page.getByLabel('Mes de producción').selectOption('2026-07-01');
 await expect(page.locator('.map-choice')).toHaveCount(0);
});
