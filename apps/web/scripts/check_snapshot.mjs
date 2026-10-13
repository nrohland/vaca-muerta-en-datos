// Validate the generated candidate through the actual frontend contracts.
// No app writes, network, price arithmetic, approval or publication.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {validateRelease,validateManifest,validatePair} from '../lib/contract.ts';
import {validatePrices} from '../lib/metrics.ts';
const {values}=parseArgs({options:{'data-dir':{type:'string'}}});
if(!values['data-dir'])throw Error('--data-dir required');
const directory=path.resolve(values['data-dir']);
const read=(name)=>readFileSync(path.join(directory,name));
const hash=(bytes)=>createHash('sha256').update(bytes).digest('hex');
const bytes=read('release.json'),priceBytes=read('prices.json');
const release=validateRelease(JSON.parse(bytes)),manifest=validateManifest(JSON.parse(read('manifest.json')));
validatePair(release,manifest);validatePrices(JSON.parse(priceBytes));
const binding=JSON.parse(read('valuation-manifest.json'));
if(hash(bytes)!==manifest.data_sha256 || binding.release_sha256!==manifest.data_sha256
 || hash(priceBytes)!==binding.prices_sha256 || binding.status!=='candidate'
 || binding.publication_approved!==false || release.valuation?.producer!=='dbt')throw Error('Candidate bindings or producer invalid');
console.log(JSON.stringify({status:'pass',publication_approved:false,data_sha256:manifest.data_sha256,
 months:manifest.source.accepted_periods.length,production_rows:release.production.length,
 entity_rows:release.entities.length,prices_sha256:hash(priceBytes)}));
