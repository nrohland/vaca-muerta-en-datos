import {test,expect} from '@playwright/test';
const base='/vaca-muerta-pulse/?tab=areas&month=2026-08-01';
test('area ranking supports search, detail deep link, persistent filters and browser back',async({page})=>{
 await page.goto(base);await expect(page.locator('.areas-ranking .ranking-item')).toHaveCount(12);
 await page.getByRole('searchbox',{name:'Buscar área'}).fill('LOMA CAMPANA');await expect(page.locator('.areas-ranking .ranking-item')).toHaveCount(1);await page.locator('.areas-ranking .ranking-item').click();await expect(page.locator('.areas-detail-heading h2')).toHaveText('LOMA CAMPANA');await expect(page).toHaveURL(/area=/);await expect(page.locator('.areas-table-scroll tbody tr')).toHaveCount(36);await page.reload();await expect(page.locator('.areas-detail-heading h2')).toHaveText('LOMA CAMPANA');await page.getByRole('button',{name:'Volver a todas las áreas'}).click();await expect(page.locator('.areas-detail')).toHaveCount(0);await page.goBack();await expect(page.locator('.areas-detail-heading h2')).toHaveText('LOMA CAMPANA');
});
test('mobile area ranking fits viewport and empty search can reset',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto(base);await expect(page.locator('.areas-dashboard')).toBeVisible();await page.getByRole('searchbox',{name:'Buscar área'}).fill('nothing matches xyz');await expect(page.locator('.areas-empty')).toBeVisible();await page.getByRole('button',{name:'Limpiar filtros'}).click();await expect(page.locator('.areas-ranking .ranking-item')).toHaveCount(12);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
