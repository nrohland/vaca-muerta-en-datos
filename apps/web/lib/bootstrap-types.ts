import type {Release,Manifest,Approval} from './contract';
import type {Prices} from './metrics';
export type Bootstrap={data:{release:Release;manifest:Manifest;approval:Approval|null};prices:Prices|null;priceError:string};
