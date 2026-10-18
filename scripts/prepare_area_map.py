"""Compile official Neuquén WFS polygons using exact reviewed area codes and names."""
import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

SOURCE = 'https://hidrocarburos.energianeuquen.gob.ar/gis'

def normalize(value):
    return re.sub(r'[^A-Z0-9]+', ' ', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().upper()).strip()

def compile_map(raw, release, retrieved_at, context_raw=None):
    catalog = defaultdict(set)
    for entry in release['entities']:
        if entry['dimension'] == 'area': catalog[entry['entity_id']].add(normalize(entry['entity_name']))
    selected = defaultdict(list)
    for feature in json.loads(raw)['features']:
        props = feature['properties']; identifier = (props.get('SIGLA') or '').strip()
        if identifier not in catalog or normalize(props.get('NOMBRE') or '') not in catalog[identifier]: continue
        geometry = feature['geometry']
        if geometry['type'] not in ('Polygon', 'MultiPolygon'): raise ValueError('Unsupported geometry')
        polygons = geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        for polygon in polygons:
            for ring in polygon:
                if len(ring)<4: raise ValueError('Invalid polygon ring')
                projected=[]
                for lon, lat, *_ in ring:
                    if not (-73<lon<-65 and -42<lat<-34): raise ValueError('Coordinates outside reviewed region')
                    projected.append((math.radians(lon), -math.log(math.tan(math.pi/4+math.radians(lat)/2))))
                selected[identifier].append(projected)
    if not selected: raise ValueError('No exact area matches')
    points=[p for rings in selected.values() for ring in rings for p in ring]
    xmin,xmax=min(p[0] for p in points),max(p[0] for p in points)
    ymin,ymax=min(p[1] for p in points),max(p[1] for p in points)
    scale=min(720/(xmax-xmin),520/(ymax-ymin)); ox=(760-(xmax-xmin)*scale)/2; oy=(560-(ymax-ymin)*scale)/2
    def path(rings):
        return ' '.join('M'+' L'.join(f'{(x-xmin)*scale+ox:.2f},{(y-ymin)*scale+oy:.2f}' for x,y in ring)+' Z' for ring in rings)
    result = {'schema_version':1,'source_url':SOURCE,'source_layer':'Hidrocarburos:Areas',
            'source_sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':retrieved_at,
            'geometry_effective_date':None,'source_crs':'EPSG:4326','projection':'Web Mercator',
            'view_box':'0 0 760 560','catalog_count':len(catalog),'unmatched_ids':sorted(set(catalog)-set(selected)),
            'features':[{'id':identifier,'path':path(rings)} for identifier,rings in sorted(selected.items())]}
    if context_raw is not None:
        matches=[f for f in json.loads(context_raw)['features'] if f['properties'].get('ADM0_A3')=='ARG']
        if len(matches)!=1 or matches[0]['geometry']['type']!='MultiPolygon': raise ValueError('Argentina context identity differs')
        rings=[]
        for polygon in matches[0]['geometry']['coordinates']:
            for ring in polygon:
                converted=[]
                for lon,lat,*_ in ring:
                    if not (-75<lon<-50 and -57<lat<-20): raise ValueError('Context coordinates outside Argentina region')
                    converted.append((math.radians(lon),-math.log(math.tan(math.pi/4+math.radians(lat)/2))))
                rings.append(converted)
        cp=[p for ring in rings for p in ring]
        cxmin,cxmax=min(p[0] for p in cp),max(p[0] for p in cp)
        cymin,cymax=min(p[1] for p in cp),max(p[1] for p in cp)
        cs=min(140/(cxmax-cxmin),230/(cymax-cymin)); cox=(160-(cxmax-cxmin)*cs)/2; coy=(250-(cymax-cymin)*cs)/2
        context_path=' '.join('M'+' L'.join(f'{(x-cxmin)*cs+cox:.2f},{(y-cymin)*cs+coy:.2f}' for x,y in ring)+' Z' for ring in rings)
        result['context']={'country':'Argentina','source_url':'https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/',
                           'source_sha256':hashlib.sha256(context_raw).hexdigest(),'scale':'1:110m', 'view_box':'0 0 160 250','path':context_path,
                           'extent':{'x':round((xmin-cxmin)*cs+cox,2),'y':round((ymin-cymin)*cs+coy,2),'width':round((xmax-xmin)*cs,2),'height':round((ymax-ymin)*cs,2)}}
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--retrieved-at',required=True)
    parser.add_argument('--context-source',type=Path)
    args=parser.parse_args();date.fromisoformat(args.retrieved_at)
    result=compile_map(args.source.read_bytes(),json.loads(args.release.read_text()),args.retrieved_at,args.context_source.read_bytes() if args.context_source else None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'matched':len(result['features']),'catalog':result['catalog_count'],'bytes':args.output.stat().st_size}))
