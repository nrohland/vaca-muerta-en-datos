import {test,expect} from './browser-fixtures';
import AxeBuilder from '@axe-core/playwright';
const base='/vaca-muerta-pulse/?tab=activity&month=2026-08-01';
test('activity has truthful physical metrics, shared ranges and filter persistence',async({page})=>{
 await page.goto(base);await expect(page.locator('.activity-data tbody tr')).toHaveCount(36);
 await expect(page.locator('.activity-kpis .kpi-card')).toHaveCount(3);
 const physical=await page.locator('.activity-kpis .kpi-value').allTextContents();
 await page.getByRole('button',{name:'Valor USD',exact:true}).click();
 await expect(page.locator('.activity-dashboard .availability-note')).toContainText('unidades físicas');
 expect(await page.locator('.activity-kpis .kpi-value').allTextContents()).toEqual(physical);
 await page.locator('.activity-range-bar').getByRole('button',{name:'Histórico',exact:true}).click();
 await expect(page.locator('.activity-data tbody tr')).toHaveCount(44);
 await page.getByRole('button',{name:'Gas',exact:true}).click();await expect(page.locator('.activity-kpis')).toContainText('m³/pozo/d');
 await page.getByRole('button',{name:'English',exact:true}).click();await expect(page.locator('.activity-heading h1')).toHaveText('Activity');
 await page.getByRole('tab',{name:'Overview',exact:true}).click();await page.getByRole('tab',{name:'Activity',exact:true}).click();
 await expect(page.getByRole('button',{name:'Gas',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.reload();await expect(page.locator('.activity-heading h1')).toHaveText('Activity');
});
test('first month omits fabricated net changes, CSV download and small screens remain usable',async({page})=>{
 await page.goto(base);await expect(page.locator('.activity-data tbody tr')).toHaveCount(36);
 const download=page.waitForEvent('download');await page.locator('.activity-download').click();expect((await download).suggestedFilename()).toContain('activity-oil-2026-08');
 await page.getByLabel('Mes de producción').selectOption('2023-01-01');await expect(page.locator('.activity-data tbody tr')).toHaveCount(1);
 await expect(page.locator('.activity-kpis .kpi-card').nth(1)).toContainText('Sin comparador');
 for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),{message:`Viewport ${width}px remains free of horizontal overflow after chart resize`}).toBe(true);}
 expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
 await page.getByRole('button',{name:'Modo oscuro',exact:true}).click();expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});
