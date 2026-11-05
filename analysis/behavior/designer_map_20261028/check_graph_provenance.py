#!/usr/bin/env python3
"""Read-only check that diagram names, hierarchy and FE_old edge exist in saved SLX."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
P=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');sample=json.loads(Path('/tmp/sar20_id4_designer_map_20261028/id4_actual.json').read_text());slx=P/'runs/az_probe_20261028T112407Z/zero_result/SarAdc_factory.slx';assert hashlib.sha256(slx.read_bytes()).hexdigest()==sample['model_sha256']
expected={'root':{'105':'EventStep','1':'Driver','111':'Calendar'},'105':{'112':'Adc','123':'Fpga','433':'Record','434':'RecordReady'},'112':{'232':'SampleRaAdvance','244':'DacCtFeedback','261':'Sar1TrialRaCt','279':'ResidueCtCompare','285':'SarDecisionTracking','297':'ChargeReturnRaReset','148':'SampleCharge','149':'RaCtState','150':'SarState'},'232':{'237':'FE_old','321':'RaAdvance'},'123':{'375':'Calibration','185':'D1CaptureBias','188':'D2InputReference','192':'DTInputReference','199':'RoundCode','200':'SaturateCode'},'375':{'383':'Train','386':'FrozenDecode'}}
with zipfile.ZipFile(slx) as z:
 for scope,names in expected.items():
  root=ET.fromstring(z.read('simulink/systems/system_'+scope+'.xml'));blocks={b.get('SID'):b for b in root.iter('Block')}
  for sid,name in names.items():assert sid in blocks and blocks[sid].get('Name')==name,(scope,sid,name)
  if scope=='112':assert all(blocks[sid].get('BlockType')=='UnitDelay' for sid in ['148','149','150'])
  if scope=='105':assert blocks['433'].get('BlockType')=='Switch' and blocks['434'].get('BlockType')=='Switch'
  if scope=='232':
   def props(e):return {p.get('Name'):p.text for p in e.findall('./P')}
   feed=[l for l in root.iter('Line') if props(l).get('Src')=='237#out:1'];assert len(feed)==1
   dst=[p.text for p in feed[0].iter('P') if p.get('Name')=='Dst'];assert '321#in:4' in dst and '322#in:1' in dst
   ra=blocks['321'];d=props(ra);assert d['FunctionName']=='behavior_backend_sfun' and 'behavior_dac_backend_parameters(P)' in d['Parameters']
archive=P/'runs/az_probe_20261028T112407Z/zero_result/source.zip'
with zipfile.ZipFile(archive) as z:
 s=z.read('current/src/physics/behavior_backend_sfun.m').decode('utf-8')
 assert 'finiteCoupling' in s and 'p.dac_coupling.enabled&&any(p.dac_coupling.tau_dac_s>0)' in s
 assert 'InputPort(4).Data' in s and 'do not evaluate InputPort(4).Data' in s
print(json.dumps({'model_sha256':sample['model_sha256'],'verified_scopes':expected,'FE_old_destinations':dst,'zero_dac_port4':'wired but off/all-zero branch does not read','snapshot_scope':'SLX/source static only; no new compilation/simulation'},ensure_ascii=False,indent=2))
