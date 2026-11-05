from pathlib import Path
import json,xml.etree.ElementTree as E
from xml.sax.saxutils import escape
D=Path('/tmp/sar20_sarpp_133342_map');d=json.loads((D/'readback.json').read_text());p=d['cases'][-1];sample=d['id4'];cmd=d['publish_hit147'];assert not d['main_integrated'] and p['bank_on'] and p['transport_on'] and not p['frozen_on'] and not p['training_on'] and p['same_slot_cache'];assert sample['record_log']==[1878,3291,213,4,1,1] and sample['code_log']==[957226] and sample['bank_code_valid_log']==[1] and cmd['meta'][8]==1;assert p['N']==8 and p['first_id']==4 and p['epoch']==1 and p['tau_dac_all_zero'] and not p['dac_coupling'] and p['az_mode']=='off' and p['mismatch'] and p['dem'] and p['dither'] and not p['ktc'] and not p['jitter'] and p['frequency_hz']==90332.03125
W,H=2200,1590
out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#365a70"/></marker></defs>','<rect width="2200" height="1590" fill="#f3f6fa"/>','<g font-family="PingFang SC,Microsoft YaHei,Arial,sans-serif" fill="#173044">']
def rect(x,y,w,h,fill='#fff',stroke='#b9ccd9',rx=10):out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
def text(x,y,s,size=18,color='#173044',weight='normal'):out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(s)}</text>')
def arrow(path,color='#365a70',dash=''):
 attr='stroke-dasharray="'+dash+'"' if dash else ''
 out.append(f'<path d="{path}" stroke="{color}" stroke-width="2.3" fill="none" {attr} marker-end="url(#a)"/>')
def dot(x,y):out.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#365a70"/>')
text(50,55,'SarPP：隔离 A 阶段候选的真实连接导览',32,weight='700')
text(50,91,'尚未晋升 current · 133342 实际保存的 RX / Bank-on N8 · 只画已存在块与已核连线',20,'#7d521d')
text(50,121,f"证据观察时间 2026-10-28 13:35:37 UTC  |  SarPP SHA256 {d['model_sha256']}  |  P SHA256 {p['P_sha256']}",14,'#4d6b7d')
# Root and event boundary
rect(35,145,2130,860,'#fff','#9eb5c4',14);text(58,179,'SarPP · root',19,weight='700')
rect(55,195,1710,755,'#fbfdff','#b7cbd8',12);text(77,227,'EventStep [105] · 仿真事件调度容器，不是芯片物理边界',19,weight='700')
# ADC
rect(85,335,190,205,'#e9f3fc','#8badc4',10);text(103,370,'Adc [112]',22,weight='700');text(103,400,'片内行为模型',16,'#486b83');text(103,431,'RAW6 / RawReady',16,'#486b83');text(103,461,'原48组ADC事件',15,'#486b83')
# Transport and internal actual blocks
rect(345,280,265,300,'#fff8ea','#d7bf89',10);text(365,314,'Transport [393]',21,weight='700');text(365,340,'片内 TX / 片外 RX',16,'#86642e');text(365,363,'合一的协议行为容器',15,'#86642e')
rect(372,390,210,58,'#fff','#d9c79e',7);text(389,425,'PinTransport [416]',17,weight='700')
rect(372,480,210,56,'#fff','#d9c79e',7);text(389,514,'TxRxState [415]',17,weight='700')
# true feedback internal
arrow('M420 448V480');arrow('M535 480V448');text(455,471,'next / old',13,'#86642e')
# Record and ready selection
rect(700,290,190,64,'#f1f6fa','#b6cad7',8);text(718,320,'Record [433]',18,weight='700');text(718,343,'P.on 选 RxRaw6',14,'#516f82')
rect(640,440,160,64,'#f1f6fa','#b6cad7',8);text(653,469,'RxRawReady',16,weight='700');text(653,491,'[431] = Ready3(2)',13,'#516f82')
rect(830,440,180,64,'#f1f6fa','#b6cad7',8);text(843,469,'RecordReady',16,weight='700');text(843,491,'[434] 选 raw_ready',13,'#516f82')
# FPGA sibling
rect(1060,290,220,240,'#edf7f0','#a9cbb1',10);text(1077,324,'Fpga [123]',21,weight='700');text(1077,353,'片外数字 / Enabled',16,'#466a50');text(1077,382,'现有名义重构',16,'#466a50')
rect(1078,409,184,67,'#fff','#c2d7c6',6);text(1090,437,'Calibration [375]',15,weight='700');text(1090,462,'Train / Frozen off',13,'#466a50')
text(1077,510,'code20 → Bank u6',15,'#466a50')
# BankOwner with external state
rect(1430,300,200,320,'#eaf3fb','#8faec5',10);text(1446,328,'BankOwner [455]',20,weight='700');text(1446,356,'u4 Record6',15);text(1446,401,'u6 FpgaCode',15);text(1446,451,'u5 RecordReady',15);text(1446,516,'u7 RxFault',15);text(1446,576,'u9 command[5]',15);text(1446,606,'u10 0[7]',15)
rect(1430,205,200,54,'#fff7df','#d7bf78',8);text(1446,237,'BankOwnerState [454]',15,'#6f571c','700')
arrow('M1475 259V300');arrow('M1580 300V259');text(1440,280,'u1 old64',12,'#6f571c');text(1550,280,'y1 next64',12,'#6f571c')
# Control blocks actually present
rect(780,728,165,57,'#f6f8fa','#bdcbd4',7);text(796,763,'Event [109]',17,weight='700')
rect(1015,728,225,68,'#f6f8fa','#bdcbd4',7);text(1033,760,'BankCommand [456]',17,weight='700');text(1033,783,'预定 command[5]',14,'#5b7385')
rect(1015,835,225,68,'#f6f8fa','#bdcbd4',7);text(1033,867,'NoDrainAck [457]',17,weight='700');text(1033,890,'常数 0[7]；无消费端确认',14,'#8b5d25')
arrow('M945 757H1015');arrow('M1240 762H1400V570H1430');arrow('M1240 869H1410V600H1430')
text(1432,648,'片外数字 Outputs；10入 / 4出',14,'#506e81');text(1432,672,'其余已连接：u2 Event[2] / u3 ActualTime[s]',14,'#506e81');text(1432,696,'u8 PublicEn；输入与控制线在此省略',14,'#506e81')
# Main ON routes (all actual)
arrow('M275 390H345');text(280,378,'Raw',13,'#506e81');arrow('M275 470H345');text(280,458,'Ready',13,'#506e81')
arrow('M610 322H700');text(620,309,'RxRaw6',14,'#506e81');arrow('M610 472H640');text(614,459,'Ready3',13,'#506e81');arrow('M800 472H830')
arrow('M890 322H1060');dot(935,322);arrow('M935 322V270H1370V350H1430');text(1160,258,'Record6 → u4',14,'#506e81')
arrow('M1010 472H1060');dot(1035,472);arrow('M1035 472V625H1350V445H1430');text(1130,616,'RecordReady → u5',14,'#506e81')
arrow('M1280 395H1430');text(1295,382,'FpgaCode → u6',14,'#506e81')
arrow('M610 548H628V690H1380V510H1430');text(807,681,'PinTransport.y7 → Transport.RxFault → BankOwner.u7',15,'#956128')
# Public outputs and root outports
for yy,pub,psid,root,rsid,signal in [(345,'PublicCode',458,'Code20',463,'y2'),(415,'PublicValid',459,'CodeValid',464,'y3'),(485,'PublicMeta',460,'CodeMeta',465,'y4')]:
 arrow(f'M1630 {yy}H1662');rect(1662,yy-22,110,44,'#fff','#adc2cf',6);text(1670,yy+6,pub,13,weight='700');arrow(f'M1772 {yy}H1830');rect(1830,yy-25,265,50,'#eaf4ee','#a6c8b0',7);text(1848,yy+7,f'{root} [{rsid}]',18,weight='700');text(1635,yy-8,signal,12,'#506e81')
text(1838,538,'CodeMeta[9]：hit, time_s, ID, epoch,',14,'#4b6d58');text(1838,562,'input_valid, slot, version, fault, status',14,'#4b6d58')
# labels and true scope
text(85,920,'图只画 RX on 的主要已连路径；OFF 时两个 Record switch 实际分别选择 Adc.Raw / Adc.Ready。',16,'#5a7282')
text(85,947,'BankOwner 与 Fpga 是 EventStep 内同级；状态64由 UnitDelay 提交，两个 h 槽是 P 中预加载的不可变参数，不存入该64字。',15,'#5a7282')
# Case configuration and stale annotation warning
rect(48,1035,2104,158,'#fff3df','#e4c798',10)
text(70,1068,'配置以 rx_bank_on/parameters.mat 为准：N8、first_id=4、epoch1、RX on、Bank on、Train/Frozen off、τDAC18全0 / DAC耦合 off。',19,'#77501e','700')
text(70,1100,'该案：Fs=5 MS/s，fin=90.33203125 kHz；失配 / DEM / dither on，AZ / kTC / jitter off；A/B 两槽同一 h、版本1/2。',17,'#77501e')
text(70,1132,'注意：SarPP 保存的 EventStep 静态文字仍写 transport=false、DEM/dither off，与该案 P 不符；本导览不使用该陈旧文字。',17,'#9a4d22','700')
text(70,1164,'各案 (transport, bank, frozen)：factory_base/off=(0,0,0)；rx_nominal=(1,0,0)；rx_old_frozen=(1,0,1)；rx_bank_on=(1,1,0)。',16,'#77501e')
# Sample evidence
rect(48,1214,2104,152,'#edf7f1','#b4d4bd',10)
text(70,1246,'已保存的实际事件示例（该案，非理想点）',20,'#275c3b','700')
text(70,1278,'hit147 / 0.600 µs：预定 PUBLISH slot2/version2、activation ID4；RecordReady=0，BankOwner meta 的 command_status=1。',17,'#275c3b')
text(70,1308,'ID4 的 RX ready=1.338 µs：Raw6=[1878,3291,213,4,1,1]；Code20=957226，CodeValid=1，slot/version=2/2。',17,'#275c3b')
text(70,1338,'Meta9=[342, 1.338e−6 s, 4, 1, 1, 2, 2, 0, 0]；根口同 ready 事件的对应关系由原生回执核对。',16,'#275c3b')
# limits
rect(48,1388,2104,158,'#fff','#c8d5de',10);text(70,1420,'证据边界',20,weight='700')
text(70,1452,'12个实际 RX ready 包含 ID0–3 预热与 ID4–11 目标；两槽同 h 只证明版本路由，不是两次独立训练。',17)
text(70,1484,'NoDrainAck 是实际零常数，不表示已有消费端 drain；未验证后台 Train、动态装载、fault 注入、退休/槽复用或下游时钟合同。',17)
text(70,1516,'Bank off 时 y2 保留 Fpga 码，根 CodeValid=0 是该禁用输出合同，不应误读为 ADC 无效；结果不是产品/硅签核。',16,'#536c7b')
out.append('</g></svg>');svg='\n'.join(out);E.fromstring(svg);(D/'sarpp_actual_map.svg').write_text(svg,encoding='utf-8');print('SVG built from saved graph and rx_bank_on logs; no live model access.')
