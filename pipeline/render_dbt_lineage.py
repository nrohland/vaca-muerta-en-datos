"""Export only project logical names/edges from a real dbt manifest, never connections."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import textwrap


def graph(manifest):
    resources={**manifest.get('nodes',{}),**manifest.get('sources',{})}
    nodes={id:{'name':n['name'],'resource_type':n['resource_type']} for id,n in resources.items()
           if n.get('package_name')=='vaca_muerta_pulse' and n.get('resource_type') in ('source','seed','model')}
    if not nodes: raise ValueError('No project graph in manifest')
    edges=sorted((p,id) for id in nodes for p in manifest['parent_map'].get(id,[]) if p in nodes)
    return {'nodes':nodes,'edges':edges}


def svg(g):
    levels={};visiting=set()
    def level(id):
        if id in levels:return levels[id]
        if id in visiting:raise ValueError('Cyclic dbt graph')
        visiting.add(id);parents=[p for p,c in g['edges'] if c==id]
        levels[id]=1+max(map(level,parents)) if parents else 0;visiting.remove(id)
        return levels[id]
    for id in g['nodes']:level(id)
    columns={n:sorted(id for id in levels if levels[id]==n) for n in set(levels.values())}
    width=(max(columns)+1)*260+40;height=max(len(ids) for ids in columns.values())*100+130
    positions={id:(20+col*260,100+i*100) for col,ids in columns.items() for i,id in enumerate(ids)}
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
      '<title id="title">Linaje dbt ejecutado — Vaca Muerta en Datos</title>',
      '<desc id="desc">Fuentes y seed a staging, universo Vaca Muerta, hechos y agregados del dashboard. No muestra tests o conexiones.</desc>',
      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#91a4b4"/></marker></defs>',
      f'<rect width="{width}" height="{height}" fill="#f7f9fc"/>',
      '<text x="20" y="30" font-family="system-ui" font-size="18" fill="#203746">Linaje del candidato histórico · generado desde manifest dbt</text>']
    long_edge=0
    for p,c in g['edges']:
        x,y=positions[p];a,b=positions[c]
        if levels[c]-levels[p]>1:
            lane=50+long_edge*10;long_edge+=1
            route=f'M {x+220} {y+32} L {x+232} {y+32} L {x+232} {lane} L {a-12} {lane} L {a-12} {b+32} L {a} {b+32}'
        else:
            route=f'M {x+220} {y+32} C {x+240} {y+32}, {a-20} {b+32}, {a} {b+32}'
        parts.append(f'<path d="{route}" fill="none" stroke="#91a4b4" stroke-width="1.5" marker-end="url(#arrow)"/>')
    for id,n in g['nodes'].items():
        x,y=positions[id];color='#fff3dc' if n['resource_type']=='seed' else '#e7f0f5' if n['resource_type']=='source' else '#ffffff'
        parts.append(f'<g><title>{escape(id)}</title><rect x="{x}" y="{y}" width="220" height="64" rx="9" fill="{color}" stroke="#b5c5d1"/>')
        parts.append(f'<text x="{x+12}" y="{y+17}" font-family="system-ui" font-size="10" fill="#607584">{n["resource_type"]}</text>')
        for i,line in enumerate(textwrap.wrap(n['name'],width=25)):
            parts.append(f'<text x="{x+12}" y="{y+35+i*15}" font-family="monospace" font-size="13" fill="#203746">{escape(line)}</text>')
        parts.append('</g>')
    return ''.join(parts)+'</svg>\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raw=a.manifest.read_bytes();manifest=json.loads(raw);g=graph(manifest)
    a.output.mkdir(parents=True,exist_ok=True)
    metadata={'manifest_sha256':hashlib.sha256(raw).hexdigest(),'generated_at':manifest['metadata']['generated_at'],
      'dbt_version':manifest['metadata']['dbt_version'],'counts':{kind:sum(n['resource_type']==kind for n in g['nodes'].values()) for kind in ('model','source','seed')},'edge_count':len(g['edges'])}
    (a.output/'linaje-dbt.svg').write_text(svg(g));(a.output/'lineage.json').write_text(json.dumps({**metadata,**g},indent=2)+'\n')
    print(json.dumps(metadata))
if __name__=='__main__':main()
