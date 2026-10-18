import {test as base,expect} from '@playwright/test';
// Browser automation must not prefetch/pan against the community tile service.
// Test the real map/geometry renderer with a local transparent raster response.
const tile=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=','base64');
export const test=base.extend({page:async({page},use)=>{
 await page.route('https://tile.openstreetmap.org/**',route=>route.fulfill({status:200,contentType:'image/png',body:tile}));
 await use(page);
}});
export {expect};
