import http from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('out');
const headerRules=JSON.parse(await readFile('vercel.json','utf8')).headers;
function applyHeaders(res,url){
 for(const rule of headerRules){
  const matches=rule.source==='/(.*)' || (rule.source==='/data/snapshots/:path*' && url.startsWith('/data/snapshots/')) || (rule.source==='/data/:file' && /^\/data\/[^/]+$/.test(url));
  if(matches)for(const {key,value} of rule.headers)res.setHeader(key,value);
 }
}
http.createServer(async(req,res)=>{try{let url=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(!url.startsWith('/vaca-muerta-pulse/'))throw Error();url=url.slice('/vaca-muerta-pulse'.length);applyHeaders(res,url);let file=path.resolve(root,'.'+url);if(url.endsWith('/'))file=path.join(file,'index.html');if(!file.startsWith(root+'/'))throw Error();const body=await readFile(file);res.setHeader('Content-Type',({'.json':'application/json','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.ico':'image/x-icon','.gz':'application/gzip'}[path.extname(file)]??'text/html'));res.end(body);}catch{res.statusCode=404;res.end('Not found');}}).listen(Number(process.env.PORT??4173),'127.0.0.1');
