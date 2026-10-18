"""Compile verified official concession geometries and interior symbol anchors."""
import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

SOURCE='https://hidrocarburos.energianeuquen.gob.ar/gis'

def normalize(value):
    return re.sub(r'[^A-Z0-9]+',' ',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().upper()).strip()

def ring_area(ring):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))/2

def inside_ring(point, ring):
    x,y=point;inside=False
    for a,b in zip(ring,ring[1:]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: inside=not inside
    return inside

def inside_polygon(point,polygon):
    return inside_ring(point,polygon[0]) and not any(inside_ring(point,hole) for hole in polygon[1:])

def interior_anchor(polygons):
    """Anchor on the largest polygon's interior, never a fabricated well location."""
    polygon=max(polygons,key=lambda p:abs(ring_area(p[0]))-sum(abs(ring_area(r)) for r in p[1:]))
    ring=polygon[0];area=ring_area(ring)
    if area:
        x=sum((a[0]+b[0])*(a[0]*b[1]-b[0]*a[1]) for a,b in zip(ring,ring[1:]))/(6*area)
        y=sum((a[1]+b[1])*(a[0]*b[1]-b[0]*a[1]) for a,b in zip(ring,ring[1:]))/(6*area)
        if inside_polygon((x,y),polygon): return [round(x,7),round(y,7)]
    # Scan-line intervals account for concavity and holes through even-odd crossings.
    low,high=min(p[1] for p in ring),max(p[1] for p in ring)
    candidates=[]
    for fraction in (.5,.25,.75,.125,.875):
        y=low+(high-low)*fraction;crossings=[]
        for boundary in polygon:
            for a,b in zip(boundary,boundary[1:]):
                if (a[1]>y)!=(b[1]>y):crossings.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        crossings.sort()
        for left,right in zip(crossings[::2],crossings[1::2]):
            point=((left+right)/2,y)
            if inside_polygon(point,polygon):candidates.append((right-left,point))
    if not candidates: raise ValueError('No verified interior anchor')
    point=max(candidates)[1]
    return [round(point[0],7),round(point[1],7)]

def compile_map(raw,release,retrieved_at,context_raw=None):
    catalog=defaultdict(set)
    for entry in release['entities']:
        if entry['dimension']=='area':catalog[entry['entity_id']].add(normalize(entry['entity_name']))
    selected=defaultdict(list)
    for feature in json.loads(raw)['features']:
        props=feature['properties'];identifier=(props.get('SIGLA') or '').strip()
        if identifier not in catalog or normalize(props.get('NOMBRE') or '') not in catalog[identifier]:continue
        geometry=feature['geometry']
        if geometry['type'] not in ('Polygon','MultiPolygon'):raise ValueError('Unsupported geometry')
        polygons=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        for polygon in polygons:
            for ring in polygon:
                if len(ring)<4 or ring[0][:2]!=ring[-1][:2]:raise ValueError('Invalid polygon ring')
                for lon,lat,*_ in ring:
                    if not (-73<lon<-65 and -42<lat<-34):raise ValueError('Coordinates outside reviewed region')
            selected[identifier].append([[[round(p[0],7),round(p[1],7)] for p in ring] for ring in polygon])
    if not selected:raise ValueError('No exact area matches')
    coordinates=[p for polygons in selected.values() for polygon in polygons for ring in polygon for p in ring]
    return {'type':'FeatureCollection','schema_version':2,'source_url':SOURCE,'source_layer':'Hidrocarburos:Areas',
            'source_sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':retrieved_at,'geometry_effective_date':None,
            'source_crs':'EPSG:4326','catalog_count':len(catalog),'unmatched_ids':sorted(set(catalog)-set(selected)),
            'bounds':[[min(p[0] for p in coordinates),min(p[1] for p in coordinates)],[max(p[0] for p in coordinates),max(p[1] for p in coordinates)]],
            'features':[{'type':'Feature','id':identifier,'properties':{'area_id':identifier,'anchor':interior_anchor(polygons)},
                         'geometry':{'type':'MultiPolygon','coordinates':polygons}} for identifier,polygons in sorted(selected.items())]}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','release','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--retrieved-at',required=True)
    args=parser.parse_args();date.fromisoformat(args.retrieved_at)
    result=compile_map(args.source.read_bytes(),json.loads(args.release.read_text()),args.retrieved_at)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'matched':len(result['features']),'catalog':result['catalog_count'],'bytes':args.output.stat().st_size}))
