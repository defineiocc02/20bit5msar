from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
D=Path('/tmp/sar20_id4_designer_map_20261028');root=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');x=json.loads((D/'id4_actual.json').read_text());ind=json.loads((root/'analysis/behavior/local_static_20261028/independent_112407.json').read_text());g=x['rows'];n=ind['final_nominal_contributions_from_public_RAW']['negative'];md=json.loads((root/'analysis/behavior/current_figures/metadata.json').read_text());assert x['model_sha256']==md['model_sha256']==ind['model_sha256']=='63190994cf15d2038f11bf5555fe12e6dde34f6e54fb1934d21ef366954ec2b6' and len(md['exported_scopes'])==14
assert g['1']['front_log'][0]==-3.0517578125e-8 and g['3']['raw_log'][0]==1024 and g['12']['raw_log'][0]==1039
assert abs(g['12']['front_log'][2]-2.1721129261363618e-13)<1e-27 and abs(g['12']['back_log'][3]-0.2559990234374998)<1e-15
assert abs(g['13']['back_log'][0]-0.2391763587845565)<1e-15 and abs(g['13']['back_log'][1]-0.18625024694449563)<1e-15
assert g['47']['record_log']==[1039,3417,42,4,1,1] and g['47']['code20']==524285 and g['47']['ready_log']==[1] and g['47']['record_ready_log']==[1]
assert all(abs(n[k]-v)<1e-15 for k,v in [('D1_v',-0.008),('D2_v',0.007984375),('DT_v',-1.171875e-5),('total_v',-2.734375e-5)]) and n['code20']==524285
out=['<svg xmlns="http://www.w3.org/2000/svg" width="1900" height="1500" viewBox="0 0 1900 1500">','<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#47677c"/></marker></defs>','<rect width="1900" height="1500" fill="#f4f7fa"/>','<g font-family="PingFang SC,Microsoft YaHei,Arial,sans-serif" fill="#173044">']
def box(x,y,w,h,fill='#fff',stroke='#c5d5e0',rx=10):out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
def text(x,y,s,size=18,c='#173044',w='normal'):out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{c}">{escape(s)}</text>')
def arrow(path):out.append(f'<path d="{path}" stroke="#47677c" stroke-width="2" fill="none" marker-end="url(#arrow)"/>')
text(45,56,'一个真实样本为何得到 524285？',32,w='700')
text(45,91,'112407 负端 ID4 / epoch1 · DC 输入 −30.517578125 nV · 4次实际预热 · N=1 · transport off',19,c='#506e81')
text(45,120,'模型 / 14张导图 SHA：63190994…54ec2b6；导图保存的是默认 N8 正弦 P，以下数值来自该次独立保存的 N1/DC P 与日志。',17,c='#506e81')
# external origin boxes
box(48,195,225,110,'#edf3f8','#a5bbca');text(70,229,'Driver · 片外',20,w='700');text(70,260,'实际 DC / 电压 V',17);text(70,289,'−30.517578125 nV',17,c='#376383')
box(48,355,225,110,'#edf3f8','#a5bbca');text(70,389,'Calendar · 日历',20,w='700');text(70,420,'行为事件 / 5 MS/s',17);text(70,449,'不是芯片物理边界',16,c='#506e81')
# EventStep boundary
box(300,155,1550,625,'#fff','#8da9bb',16);text(325,190,'EventStep · 事件调度容器（非芯片边界）',20,w='700')
arrow('M273 250H300');arrow('M273 410H300')
# ADC region
box(330,210,850,530,'#f1f7fc','#9bb9ce',12);text(352,243,'Adc · 片内行为模型',21,w='700');text(352,269,'以下是当前六个同层子系统的阅读顺序，省略非本路径连线。',15,c='#526e81')
stages=[(355,290,'1  SampleRaAdvance','Sample / RaAdvance'),(620,290,'2  DacCtFeedback','Due / Dac / CtFeedback'),(885,290,'3  Sar1TrialRaCt','Preconvert / Trial / RA'),(355,414,'4  ResidueCtCompare','Compare1 / Compare2'),(620,414,'5  SarDecisionTracking','SAR2 / Tracking / Raw'),(885,414,'6  ChargeReturnRaReset','Return / Reset')]
for xx,yy,title,sub in stages:
 box(xx,yy,240,92,'#fff','#bad0df',8);text(xx+13,yy+33,title,17,w='700');text(xx+13,yy+61,sub,15,c='#526e81')
box(355,535,770,69,'#fff7df','#d7bd7a',8);text(374,563,'已锁存责任：SampleCharge[353] · RaCtState[48] · SarState[51]',17,c='#6c551f',w='700');text(374,588,'UnitDelay 输出是此前旧态；本次完整提交后状态没有单独保存。',15,c='#6c551f')
text(355,642,'FE_old → RaAdvance.u4 是已有线；本例 τDAC=0、coupling off，u4 不读取。',16,c='#516b7b')
text(355,670,'阶段的 advance / next 是当前计算候选，不把预测端点或 BackLog 当成已提交状态。',16,c='#6e5891')
text(355,698,'RaPreLog 未完整保存；43.75 ns 的 VX/VY 来自 BackLog。',16,c='#956230')
# Actual Record/RecordReady switches and digital boundary
box(1195,300,155,52,'#f9fbfd','#a6b9c5',8);text(1215,332,'Record',17,w='700')
box(1195,392,155,52,'#f9fbfd','#a6b9c5',8);text(1209,424,'RecordReady',16,w='700');text(1209,468,'transport off',14,c='#526e81')
arrow('M1180 326H1195');arrow('M1180 418H1195')
box(1370,210,445,530,'#f0f7f3','#a5c4b0',12);text(1392,243,'Fpga · 片外数字',21,w='700');text(1392,270,'输入为同 ID / epoch 的 Raw6',15,c='#4c745a')
box(1393,292,398,112,'#fff','#bdd2c2',8);text(1410,320,'已有算术块（分组说明）',17,w='700');text(1410,347,'D1CaptureBias / D2InputReference',15,c='#4d6d58');text(1410,370,'DTInputReference / RoundCode / SaturateCode',15,c='#4d6d58');text(1410,392,'本次分项仅按 RAW / P 核验',14,c='#4d6d58')
box(1393,437,398,93,'#fff','#bdd2c2',8);text(1410,470,'Calibration（真实已有层级）',17,w='700');text(1410,500,'Train / FrozenDecode 本例均 off',15,c='#4d6d58')
text(1395,582,'[实] code_log = 524285',21,c='#226045',w='700');text(1395,610,'该码与 valid RAW 同一 ready 行',15,c='#4d6d58')
arrow('M1350 326H1370');arrow('M1350 418H1370');arrow('M1588 404V437')
text(327,764,'结构图只表示真实块的层级和读图方向；未画全部信号，事件节点不等于晶体管波形。',15,c='#607b8d')
# event timeline
text(48,833,'实际 ID4 事件链',22,w='700');text(267,833,'t=0 为 CNV=0.8 µs；只使用该次保存日志',16,c='#506e81')
cards=[(48,'0 ns','CNV / Sample','held = −30.517578125 nV','[实] front_log'),(410,'15 ns','SAR1 首次细判','Vres = −30.517578128 nV','D1raw = 1024 [实]'),(772,'31.25 ns','RA start','Qres = +0.217211293 pC','target = +0.255999023 V [实]'),(1134,'43.75 ns','D2 prepare','VX = +0.239176359 V','VY = +0.186250247 V [实]'),(1496,'86.25 ns','RAW ready','RAW = [1039,3417,42]','code20 = 524285 [实]')]
for xx,t,h,a,b in cards:
 box(xx,856,340,190,'#fff','#bacdda',9);text(xx+15,885,t,20,w='700');text(xx+15,914,h,16,c='#526e81');text(xx+15,950,a,17,c='#245b7c',w='700');text(xx+15,980,b,16,c='#245b7c')
for xx in (388,750,1112,1474):arrow(f'M{xx} 950h20')
text(63,1020,'front_log.held',14,c='#60798a');text(425,1020,'bit4=0 由写位推断；CMP未单独存',14,c='#91672a');text(787,1020,'FrontLog Qres / BackLog target',14,c='#60798a');text(1149,1020,'BackLog；非 RaPre 完整日志',14,c='#91672a');text(1511,1020,'ID4 / epoch1 / valid1',14,c='#60798a')
# result + epistemics
box(48,1070,1804,155,'#eff7f1','#b5d2bd',10);text(68,1105,'仅核验：由最终 RAW 与保存的 P.digital 重建名义贡献（本次分项日志未完整保存）',19,c='#2b6740',w='700')
text(68,1144,'D1：−8000 µV　 +　D2：+7984.375 µV　 +　DT：−11.71875 µV　 =　−27.34375 µV',21,c='#2b6740')
text(68,1182,'FSR=8.192 V → 名义 LSB=7.8125 µV → clip(round(2¹⁹ − 3.5)) = 524285；实际码直接取 code_log。',18,c='#2b6740')
box(48,1248,1804,202,'#fff5e7','#e1c39b',10);text(70,1284,'读数与状态边界',20,c='#8b521f',w='700')
text(70,1317,'[实] 已保存的行为仿真日志　 [推] D1 bit / 名义分项由公开 RAW 推算　 [待提交] 本事件阶段 next 不等于已回读提交态。',17,c='#674b35')
text(70,1348,'ADC RawReady 与 record-ready 同为 0.88625 µs；本次无 RX 传输。RaPreLog、逐比较器独立位和完整提交状态未完整保存。',17,c='#674b35')
text(70,1379,'源：112407 保存 P / 9 路 timeseries 与独立逐事件报告；四次预热不证明一般稳态，行为模型不等于硅片/PDK 测量。',17,c='#674b35')
text(70,1410,'图示只使用当前真实层级；Bank / M1 未作为本路径组件，RA 后没有新增采样保持。',17,c='#674b35')
out.append('</g></svg>');s='\n'.join(out);ET.fromstring(s);(D/'id4_designer_map.svg').write_text(s,encoding='utf-8');print('SVG generated after actual sample assertions; no native model operations.')
