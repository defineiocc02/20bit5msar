#!/usr/bin/env python3
"""Independent SLX XML scope diff; does not execute MATLAB or modify either graph."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

LIMIT = 300_000_000
GEOMETRY = {'Position', 'ZOrder', 'Location', 'ZoomFactor', 'Points', 'Labels'}
MODEL_METADATA = {'ModelUUID', 'ModifiedByFormat', 'ModifiedDateFormat', 'ModelVersionFormat'}
SOURCES = [('116',1),('148',1),('232',3),('244',1),('261',3),('297',3),
           ('149',1),('232',1),('244',4),('261',4),('297',1),('232',4)]

def data(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>LIMIT:raise ValueError(f'unsafe/oversized {p}')
    b=p.read_bytes()
    if len(b)>LIMIT:raise ValueError(f'file grew past limit {p}')
    return b

def member(z,name):
    item=z.getinfo(name)
    if item.file_size>LIMIT:raise ValueError(f'oversized XML {name}')
    return z.read(item)

def canonical(node,model=False):
    if node.tag=='P' and (node.get('Name') in GEOMETRY or (model and node.get('Name') in MODEL_METADATA)):return None
    attrs=tuple(sorted(node.attrib.items()))
    text=(node.text or '').strip()
    children=tuple(x for x in (canonical(c,model) for c in node) if x is not None)
    return node.tag,attrs,text,children

def graph(raw):
    root=ET.fromstring(raw);blocks={x.get('SID'):x for x in root.findall('Block')};edges=[];edge_meta={}
    def visit(node,source=None,inherited=None):
        values={p.get('Name'):p.text for p in node.findall('P')};source=values.get('Src',source)
        meta=dict(inherited or {})
        meta.update({k:v for k,v in values.items() if k not in GEOMETRY and k not in {'Src','Dst'}})
        if 'Dst' in values:
            edge=(source,values['Dst']);edges.append(edge);edge_meta.setdefault(edge,[]).append(tuple(sorted(meta.items())))
        for branch in node.findall('Branch'):visit(branch,source,meta)
    for line in root.findall('Line'):visit(line)
    return root,blocks,Counter(edges),edge_meta

def parameters(block):return {x.get('Name'):(x.text or '') for x in block.findall('P')}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True);ap.add_argument('--modified',required=True)
    ap.add_argument('--inputs',required=True);ap.add_argument('--build-receipt',required=True);ap.add_argument('--output',required=True)
    a=ap.parse_args();out=Path(a.output)
    if out.exists():raise ValueError('refuse to overwrite audit output')
    inputs=json.loads(data(a.inputs));receipt=json.loads(data(a.build_receipt));base=data(a.baseline);new=data(a.modified)
    bh=hashlib.sha256(base).hexdigest();nh=hashlib.sha256(new).hexdigest()
    for key in ('model_sha256','P_used_sha256','normal_simout_sha256','source_manifest_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}',str(inputs[key])):raise ValueError('invalid input SHA length/format: '+key)
    if bh!=inputs['model_sha256'] or nh!=receipt.get('model_sha256') or receipt.get('status')!='SAVED_PENDING_XML_AUDIT':raise ValueError('baseline or saved-graph receipt identity mismatch')
    with zipfile.ZipFile(a.baseline) as x,zipfile.ZipFile(a.modified) as y:
        xsys={n for n in x.namelist() if n.startswith('simulink/systems/system_') and n.endswith('.xml')};ysys={n for n in y.namelist() if n.startswith('simulink/systems/system_') and n.endswith('.xml')}
        if xsys!=ysys:raise ValueError('system XML inventory changed')
        added_blocks=[];added_edges=[]
        for name in sorted(xsys):
            xr,xb,xe,xmeta=graph(member(x,name));yr,yb,ye,ymeta=graph(member(y,name))
            for edge,meta in xmeta.items():
                if sorted(meta)!=sorted(ymeta.get(edge,[])):raise ValueError(f'old line attributes changed: {name} {edge}')
            old_ids=set(xb);new_ids=set(yb)
            if not old_ids<=new_ids:raise ValueError('existing block removed: '+name)
            for sid in old_ids:
                if canonical(xb[sid])!=canonical(yb[sid]):raise ValueError(f'existing block changed: {name} SID {sid}')
            new_ids-=old_ids
            if name!='simulink/systems/system_112.xml' and (new_ids or xe!=ye):raise ValueError('unexpected graph change outside ADC: '+name)
            if name=='simulink/systems/system_112.xml':
                if len(new_ids)!=2:raise ValueError('expected exactly 2 new blocks')
                added_blocks=[yb[s] for s in new_ids]
                mux=[b for b in added_blocks if b.get('Name')=='PhysicalStateMux' and b.get('BlockType')=='Mux']
                sink=[b for b in added_blocks if b.get('Name')=='PhysicalStateTap' and b.get('BlockType')=='ToWorkspace']
                if len(mux)!=1 or len(sink)!=1:raise ValueError('missing expected Mux or ToWorkspace')
                mp,sp=parameters(mux[0]),parameters(sink[0])
                if mp.get('Inputs')!='12' or any(sp.get(k)!=v for k,v in {'VariableName':'physical_state_tap','SaveFormat':'Timeseries','MaxDataPoints':'inf','SampleTime':'-1'}.items()) or sp.get('Decimation','1')!='1' or receipt.get('observer_decimation')!='1':raise ValueError('observer parameters/readback differ')
                added=ye-xe;removed=xe-ye
                expected=Counter([(f'{sid}#out:{port}',f'{mux[0].get("SID")}#in:{i}') for i,(sid,port) in enumerate(SOURCES,1)]+[(f'{mux[0].get("SID")}#out:1',f'{sink[0].get("SID")}#in:1')])
                if removed or added!=expected:raise ValueError(f'old edges removed or new edges differ: removed={removed}, added={added}')
                added_edges=list(added.elements())
        ignored=[];dictionary_uuids=[];xn=set(x.namelist());yn=set(y.namelist())
        if xn!=yn:raise ValueError('SLX member inventory changed')
        for name in sorted(xn-xsys):
            if name.startswith('metadata/') or name=='simulink/windowsInfo.xml':
                if member(x,name)!=member(y,name):ignored.append(name)
                continue
            before=member(x,name);after=member(y,name)
            if name.endswith(('.xml','.rels')):
                left=ET.fromstring(before);right=ET.fromstring(after)
                if name=='simulink/modelDictionary.xml':
                    ln=list(left.iter());rn=list(right.iter())
                    if len(ln)!=3 or len(rn)!=3 or [n.tag for n in ln]!=['MF0','System','Interface'] or [n.tag for n in rn]!=['MF0','System','Interface']:
                        raise ValueError('unexpected model dictionary structure')
                    for lnode,rnode in zip(ln[1:],rn[1:]):
                        lu=lnode.attrib.pop('uuid',None);ru=rnode.attrib.pop('uuid',None)
                        if not isinstance(lu,str) or not isinstance(ru,str) or not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',lu) or not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',ru):
                            raise ValueError('invalid dictionary UUID')
                        if lu!=ru:dictionary_uuids.append({'element':lnode.tag,'before':lu,'after':ru})
                if canonical(left,name=='simulink/blockdiagram.xml')!=canonical(right,name=='simulink/blockdiagram.xml'):
                    raise ValueError('non-system XML changed: '+name)
            elif before!=after:raise ValueError('non-XML SLX member changed: '+name)
    result={'status':'XML_SCOPE_PASS_PENDING_N8','baseline_sha256':bh,'model_sha256':nh,'input_manifest_sha256':hashlib.sha256(data(a.inputs)).hexdigest(),'added_blocks':[{'sid':b.get('SID'),'name':b.get('Name'),'type':b.get('BlockType')} for b in added_blocks],'added_edges':added_edges,'observer_width':2015,'old_block_parameters_and_edges':'unchanged','configset':'unchanged','workspace_bytes':'unchanged','ignored_UI_metadata':ignored,'observed_save_regenerated_dictionary_uuids':dictionary_uuids,'decimation_xml_explicit':('Decimation' in sp),'decimation_runtime_readback':receipt.get('observer_decimation'),'scope':'static saved graph XML only; N8 nondisturbance still required'}
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,ET.ParseError,zipfile.BadZipFile) as ex:raise SystemExit('GRAPH_AUDIT_FAIL: '+str(ex))
