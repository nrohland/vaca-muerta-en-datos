import {test,expect} from '@playwright/test';

test('static security headers protect documents and preserve snapshot caching',async({page,request})=>{
 const response=await page.goto('/vaca-muerta-pulse/');
 expect(response?.headers()['x-content-type-options']).toBe('nosniff');
 expect(response?.headers()['x-frame-options']).toBe('DENY');
 expect(response?.headers()['referrer-policy']).toBe('strict-origin-when-cross-origin');
 expect(response?.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
 expect(response?.headers()['content-security-policy']).toContain("object-src 'none'");
 expect(response?.headers()['content-security-policy']).toContain('https://tile.openstreetmap.org');
 await expect(page.locator('.kpi-card--primary')).toBeVisible();
 const manifestResponse=await request.get('/vaca-muerta-pulse/data/manifest.json');
 expect(manifestResponse.headers()['cache-control']).toContain('must-revalidate');
 const manifest=await manifestResponse.json();
 const shard=await request.get('/vaca-muerta-pulse/data/'+manifest.delivery.overview.path);
 expect(shard.headers()['cache-control']).toContain('immutable');
 expect(shard.headers()['x-content-type-options']).toBe('nosniff');
});

 test('build hashes reject arbitrary inline JavaScript',async({page})=>{
 await page.goto('/vaca-muerta-pulse/');
 const policy=await page.locator('meta[name=build-script-policy]').getAttribute('content');
 expect(policy).toContain('sha256-');
 expect(policy).not.toContain('unsafe-inline');
 const executed=await page.evaluate(()=>{const s=document.createElement('script');s.textContent='document.documentElement.dataset.untrustedScript=String(true)';document.head.appendChild(s);return document.documentElement.dataset.untrustedScript;});
 expect(executed).toBeUndefined();
 });
