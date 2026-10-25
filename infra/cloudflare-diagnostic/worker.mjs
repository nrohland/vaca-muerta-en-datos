// Transport diagnosis only. No CSV, secrets, storage, redirects or freshness writes.
const TARGETS = Object.freeze({
  '/probe/resource': 'https://datos.energia.gob.ar/api/3/action/resource_show?id=fb7a47a0-cba9-4667-a004-6f6c1c346c23',
  '/probe/catalogue': 'https://datos.energia.gob.ar/api/3/action/package_show?id=c846e79c-026c-4040-897f-1ad3543b407c',
});
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const headers = {'Cache-Control':'no-store'};
    if (request.method !== 'GET') return new Response('Method not allowed', {status:405,headers:{...headers,Allow:'GET'}});
    if (url.search) return new Response('Query parameters not accepted', {status:400,headers});
    if (url.pathname === '/health') return Response.json({diagnostic:true,ingress_colo:request.cf?.colo ?? null}, {headers});
    const target = TARGETS[url.pathname];
    if (!target) return new Response('Not found',{status:404,headers});
    const start = Date.now();
    const common = {target,ingress_colo:request.cf?.colo ?? null,csv_verified:false,freshness_updated:false};
    try {
      const upstream = await fetch(target, {
        method:'GET', redirect:'manual', signal:AbortSignal.timeout(20000),
        headers:{Accept:'application/json','User-Agent':'VacaMuertaEnDatos-connectivity-diagnostic/1.0'},
      });
      const status = upstream.status;
      const redirect = status >= 300 && status < 400;
      await upstream.body?.cancel();
      return Response.json({...common,http_status:status,redirect_not_followed:redirect,seconds:(Date.now()-start)/1000}, {status:status===200?200:502,headers});
    } catch (error) {
      return Response.json({...common,error:error.name==='TimeoutError'?'timeout':'fetch_failed',seconds:(Date.now()-start)/1000},{status:502,headers});
    }
  }
};
