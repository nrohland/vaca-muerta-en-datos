import {test,expect} from '@playwright/test';
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
 await page.goto(base+'&tab=areas');const polygons=page.locator('.area-map path');await expect(polygons).toHaveCount(68);
 await expect(page.locator('.area-map-card')).toContainText('68/88');
 await polygons.first().focus();await expect(page.locator('.map-readout')).toContainText('AGUADA FEDERAL');
 await polygons.first().press('Enter');await expect(page).toHaveURL(/area=AFED/);
 await expect(page.locator('.areas-detail h2')).toContainText('AGUADA FEDERAL');
 await page.getByRole('button',{name:'Valor USD',exact:true}).click();await expect(page.locator('.area-map-card')).toContainText('USD');
 await page.getByRole('button',{name:'English',exact:true}).click();await expect(page.locator('.area-map-card h2')).toContainText('Area map');
 await page.reload();await expect(polygons).toHaveCount(68);await expect(page).toHaveURL(/area=AFED/);
});
test('activity exposes meaningful comparisons and expands the full table',async({page})=>{
 await page.goto(base+'&tab=activity');await expect(page.locator('.activity-count-plot .recharts-bar')).toHaveCount(1);
 await expect(page.locator('.activity-average-plot .recharts-bar-rectangle')).toHaveCount(2);
 await expect(page.locator('.activity-data .trend-positive').first()).toContainText('+');
 await page.getByRole('button',{name:'Expandir tabla',exact:true}).click();await expect(page.locator('.activity-table-scroll')).toHaveClass(/is-expanded/);
 await page.getByLabel('Mes de producción').selectOption('2023-01-01');await expect(page.locator('.activity-average-plot .recharts-bar-rectangle')).toHaveCount(1);
 await expect(page.locator('.activity-dashboard')).toContainText('Sin promedio válido para el mes base');
});
test('map and all detail views stay within a narrow English dark viewport',async({page})=>{
 await page.setViewportSize({width:320,height:812});await page.goto(base+'&tab=areas');
 await expect(page.locator('.map-context')).toContainText('Argentina');
 await page.getByRole('button',{name:'English',exact:true}).click();await page.getByRole('button',{name:'Dark mode',exact:true}).click();
 for(const name of ['Areas','Activity','Production','Operators','Overview']){
  await page.getByRole('tab',{name,exact:true}).click();
  await expect(page.getByRole('tabpanel')).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
});
