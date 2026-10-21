import {validateRelease, validatePair, sha256, type Release, type Manifest, type Entity, type Fluid, type Dimension} from './contract.ts';
export type DeliveryRef = {path:string;sha256:string;bytes:number;decoded_bytes:number;rows:number};
export type Delivery = {schema_version:1;release_sha256:string;overview:DeliveryRef;entities:Record<string,DeliveryRef>};
export const shardKey = (fluid:Fluid, dimension:Dimension) => `${fluid}-${dimension}`;
export function validateDelivery(value:unknown, releaseHash:string):Delivery {
 const v=value as Delivery;
 if(!v||v.schema_version!==1||v.release_sha256!==releaseHash||!v.entities)throw Error('Entrega no corresponde a esta versión.');
 const keys=['oil-company','oil-area','gas-company','gas-area'];
 if(Object.keys(v.entities).sort().join()!==[...keys].sort().join())throw Error('Detalle incompleto.');
 for(const [key,r] of [['overview',v.overview],...keys.map(k=>[k,v.entities[k]])] as [string,DeliveryRef][]){
  if(!r||!Number.isSafeInteger(r.bytes)||r.bytes<=0||r.bytes>8*1024**2||!Number.isSafeInteger(r.decoded_bytes)||r.decoded_bytes<=0||r.decoded_bytes>32*1024**2||!Number.isSafeInteger(r.rows)||r.rows<0||!/^[a-f0-9]{64}$/.test(r.sha256)||r.path!==`snapshots/${releaseHash}/${key}-${r.sha256.slice(0,16)}.json.gz`)throw Error('Referencia de entrega inválida.');
 }
 return v;
}
export async function readDelivery(ref:DeliveryRef, base:string, signal?:AbortSignal):Promise<unknown> {
 const response=await fetch(`${base}/data/${ref.path}`,{signal});
 if(!response.ok)throw Error('No pudimos cargar los agregados.');
 const reader=response.body?.getReader();if(!reader)throw Error('Datos no disponibles.');
 const chunks:Uint8Array[]=[];let size=0;
 try {while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>ref.bytes)throw Error('Tamaño de entrega inválido.');chunks.push(value);}}
 finally{await reader.cancel();}
 if(size!==ref.bytes)throw Error('Tamaño de entrega inválido.');
 const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
 if(await sha256(bytes.buffer)!==ref.sha256)throw Error('La versión no coincide con su manifiesto.');
 const decodedReader=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
 const decoded:Uint8Array[]=[];let decodedSize=0;
 try{while(true){const {done,value}=await decodedReader.read();if(done)break;decodedSize+=value.length;if(decodedSize>ref.decoded_bytes)throw Error('Tamaño descomprimido inválido.');decoded.push(value);}}
 finally{await decodedReader.cancel();}
 if(decodedSize!==ref.decoded_bytes)throw Error('Tamaño descomprimido inválido.');
 const plain=new Uint8Array(decodedSize);offset=0;for(const c of decoded){plain.set(c,offset);offset+=c.length;}
 return JSON.parse(new TextDecoder().decode(plain));
}
export function validateOverview(value:unknown, manifest:Manifest, delivery:Delivery):Release {
 const release=validateRelease(value);validatePair(release,manifest);
 if(release.entities.length!==delivery.overview.rows||release.entities.some(r=>r.volume_rank>5))throw Error('Resumen de entrega inválido.');
 return release;
}
export function validateEntities(value:unknown, overview:Release, ref:DeliveryRef, fluid:Fluid, dimension:Dimension):Entity[] {
 if(!Array.isArray(value)||value.length!==ref.rows||value.some(r=>r.fluid!==fluid||r.dimension!==dimension))throw Error('Detalle de entrega inválido.');
 const release=validateRelease({...overview,entities:value});
 const known=new Map(release.entities.map(r=>[`${r.entity_id}/${r.periodo}`,r]));
 for(const row of overview.entities.filter(r=>r.fluid===fluid&&r.dimension===dimension)){
  if(JSON.stringify(known.get(`${row.entity_id}/${row.periodo}`))!==JSON.stringify(row))throw Error('Detalle no coincide con Resumen.');
 }
 return release.entities;
}

// Component-owned cache for the bounded set of public, hash-keyed detail shards.
// Keep in-flight and successful promises; failures must remain retryable.
export function createRequestCache<T>() {
 const requests=new Map<string,Promise<T>>();
 return {read(key:string,load:()=>Promise<T>):Promise<T>{
  const existing=requests.get(key);if(existing)return existing;
  const request=Promise.resolve().then(load).catch(error=>{requests.delete(key);throw error;});
  requests.set(key,request);return request;
 }};
}
