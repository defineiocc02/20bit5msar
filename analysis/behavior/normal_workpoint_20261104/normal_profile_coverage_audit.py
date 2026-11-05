#!/usr/bin/env python3
"""Read-only audit of the actual prepared SAR20 normal P (MAT v7.3).

No MATLAB, no simulation, no changes to production. A table is created only
after the P, assumptions, exact source files and five function-gate receipts
are hash-bound. A prepared P is not an actual graph simulation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import h5py
import numpy as np

ROOT = Path("/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020")
WORK = ROOT / "analysis/behavior/normal_workpoint_20261104"
CANDIDATE = ROOT / "analysis/behavior/merged_ou_rc_20261104_toyFVb/candidate"
LIMIT = 300_000_000
GATES = {
    "test_single_rc_ktc": "passed",
    "test_joint_ou_az_dac": "passed",
    "test_joint_ou_rc_return": "passed",
    "test_comparator_single": "passed",
    "test_normal_10v": "FUNCTION_ASSERTIONS_PASSED",
}
SOURCES = (
    "current/src/frontend/behavior_frontend_init.m",
    "current/src/frontend/behavior_frontend_step.m",
    "current/src/physics/behavior_backend_step.m",
    "current/src/physics/behavior_backend_stage.m",
    "current/src/physics/behavior_dac_forcing_from_frontend.m",
    "current/src/physics/sar20_ra_ou_increment.m",
    "current/src/physics/sar20_cdac2_network.m",
    "current/src/control/behavior_comparator_sample.m",
    "current/src/control/behavior_control_stage.m",
    "current/src/model/behavior_prepare_configuration.m",
    "current/src/model/behavior_ra_noise_guard.m",
)

def require(condition, message):
    if not bool(condition):
        raise ValueError(message)

def small(path: Path):
    require(path.is_file() and not path.is_symlink(), f"missing or symlink: {path}")
    require(path.stat().st_size <= LIMIT, f"file exceeds 300 MB: {path}")

def sha(path: Path):
    small(path)
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()

def js(path: Path):
    small(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))

def get(f, path):
    obj=f[path]
    require(isinstance(obj,h5py.Dataset),f"{path} is not a dataset")
    a=np.asarray(obj[()])
    require(h5py.check_dtype(ref=obj.dtype) is None,f"{path} uses unsupported refs")
    cls=obj.attrs.get("MATLAB_class",b"")
    if isinstance(cls,(bytes,np.bytes_)):
        cls=cls.decode()
    if cls=="char":
        return "".join(chr(int(x)) for x in a.ravel(order="F"))
    if a.size==1:
        result=a.ravel()[0].item()
        return bool(result) if cls=="logical" else result
    return a.T

def array(f,path):
    return np.asarray(get(f,path),dtype=np.float64)

def scalar(f,path):
    x=get(f,path)
    require(np.isscalar(x) and not isinstance(x,str),f"not numeric scalar: {path}")
    return float(x)

def close(actual, expected, label, rtol=1e-12, atol=0.0):
    require(np.allclose(actual,expected,rtol=rtol,atol=atol,equal_nan=False),
            f"{label} mismatch: actual={actual}, expected={expected}")

def mdlink(label, path):
    return f"[{label}](<{path}>)"

def calendar_counts(f):
    """Read the saved MATLAB struct-array event names without executing MATLAB."""
    g=f['P/adc_groups']
    refs=np.asarray(g['events'][()]).ravel()
    require(refs.size==48,'actual saved ADC groups must contain 48 event times')
    counts={name:0 for name in ('d2_decide','ta_compare','ta_feedback')}
    for ref in refs:
        node=f[ref]['type']
        if isinstance(node,h5py.Dataset) and h5py.check_dtype(ref=node.dtype) is not None:
            names=[''.join(chr(int(x)) for x in np.asarray(f[q][()]).ravel())
                   for q in np.asarray(node[()]).ravel()]
        else:
            names=[''.join(chr(int(x)) for x in np.asarray(node[()]).ravel())]
        for name in names:
            if name in counts:counts[name]+=1
    require(list(counts.values())==[12,8,7],f'unexpected saved ADC calendar: {counts}')
    return counts

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile",type=Path,required=True,
                    help="mirrored profile folder with complete.json and MAT files")
    ap.add_argument("--gates",type=Path,required=True,action="append",
                    help="mirrored gates folder; repeat to use non-duplicated gates from a retry")
    ap.add_argument("--execution-status",type=Path,required=True,action="append",
                    help="controller status whose completed phases were exit-0/postverified; repeat across retries")
    ap.add_argument("--output",type=Path,default=WORK/"NORMAL_NONIDEALITY_COVERAGE.md")
    args=ap.parse_args()
    profile=args.profile.resolve(strict=True)
    gate_roots=[x.resolve(strict=True) for x in args.gates]
    status_paths=[x.resolve(strict=True) for x in args.execution_status]
    statuses=[js(x) for x in status_paths]
    for name in (*GATES,"profile"):
        require(any(name in state.get("completed",[]) for state in statuses),
                f"no controller recorded exit-0/postverified completion for {name}")
    out=args.output
    require(out.parent.resolve(strict=True)==WORK.resolve(strict=True),
            "output must be directly in the one normal_workpoint directory")
    require(not out.exists(),f"refuse to overwrite {out}")
    receipt=js(profile/"complete.json")
    require(receipt.get("status")=="prepared","profile is not prepared")
    for filename, key in (("normal_P.mat","normal_P_sha256"),("ideal_P.mat","ideal_P_sha256"),
                          ("assumptions.mat","assumptions_sha256")):
        require(sha(profile/filename)==receipt.get(key),f"{filename} hash differs")
    source=WORK/"windows_gate_asrun/normal_parameters.m"
    require(sha(source)==receipt.get("normal_parameters_sha256"),"as-run parameter source hash differs")
    manifest_path=CANDIDATE/"MANIFEST.json"
    manifest=js(manifest_path)
    require(sha(manifest_path)==receipt.get("candidate_manifest_sha256"),"candidate manifest hash differs")
    source_map=manifest["files"]
    for rel in SOURCES:
        require(rel in source_map and sha(CANDIDATE/rel)==source_map[rel],f"candidate source differs: {rel}")
    gate_evidence={}
    for name,expected in GATES.items():
        matches=[root/name for root in gate_roots if (root/name/"complete.json").is_file()]
        require(len(matches)==1,f"need exactly one mirrored passed gate for {name}; got {len(matches)}")
        directory=matches[0]
        gate=js(directory/"complete.json")
        require(gate.get("status")==expected and gate.get("test")==name,
                f"{name} not passed as required")
        require(gate.get("model_loaded") is False and isinstance(gate.get("pid"),int)
                and gate["pid"]>0 and gate["pid"]!=27628,
                f"{name} lacks its recorded headless/no-model boundary")
        require(gate.get("candidate_manifest_sha256")==receipt["candidate_manifest_sha256"],
                f"{name} uses a different candidate")
        report_hash=sha(directory/"report.mat")
        require(report_hash==gate.get("report_sha256"),
                f"{name} report hash differs")
        if name=="test_normal_10v":
            require(report_hash==receipt.get("range_test_sha256"),
                    "profile does not bind this exact 10 V gate report")
        gate_evidence[name]=directory/"complete.json"

    with h5py.File(gate_evidence['test_single_rc_ktc'].parent/'report.mat','r') as gate:
        gate_n=int(scalar(gate,'report/stat_n'))
        gate_var=scalar(gate,'report/stationary_var')
        gate_lag=scalar(gate,'report/lag1_cov')
        gate_lag_ref=scalar(gate,'report/expected_lag1')

    with h5py.File(profile/"normal_P.mat","r") as p, h5py.File(profile/"assumptions.mat","r") as a, \
            h5py.File(profile/"ideal_P.mat","r") as ideal:
        P="P/";A="assumptions/"
        n=scalar(p,P+"N");fs=scalar(p,P+"fs_hz");ts=scalar(p,P+"Ts_s")
        require(n==8 and fs==5e6 and ts==200e-9,"not the specified N8/5 MS/s profile")
        require(scalar(p,P+"first_id")==4 and scalar(p,P+"epoch")==1,"unexpected record identity")
        require(scalar(p,P+"front/single_bank")==1 and scalar(p,P+"control/single_bank")==1,
                "not the fixed single array")
        require(scalar(p,P+"front/single_guard_s")==2e-9,"unexpected guard")
        close(scalar(p,P+"digital/fsr_diff_v"),10.0,"digital FSR")
        close(scalar(p,P+"fsr_diff_v"),10.0,"public FSR")
        close(scalar(p,P+"front/vref_v"),5.0,"frontend Vref")
        close(scalar(p,P+"digital/vref_v"),5.0,"digital Vref")
        close(scalar(p,P+"control/sar1/delta_v"),10/1024,"coarse delta")
        close(scalar(p,P+"input/amplitude_v"),5*10**(-1/20),"input amplitude")
        close(scalar(p,P+"input/frequency_hz"),97656.25,"input frequency")
        require(scalar(p,P+"digital/d1_bias_v")==0,"1039 Cu bias must be zero")
        counts=calendar_counts(p)
        dp=p[P+'digital'];di=ideal['ideal/digital']
        require(set(dp.keys())==set(di.keys()),'normal and ideal digital field inventories differ')
        for key in dp.keys():
            if key=='az_mode':continue
            x,y=dp[key],di[key]
            require(isinstance(x,h5py.Dataset) and isinstance(y,h5py.Dataset) and
                    h5py.check_dtype(ref=x.dtype) is None and h5py.check_dtype(ref=y.dtype) is None,
                    f'unsupported digital field: {key}')
            xv,yv=np.asarray(x[()]),np.asarray(y[()])
            require(xv.dtype==yv.dtype and xv.shape==yv.shape and xv.tobytes()==yv.tobytes(),
                    f'nominal digital field changed: {key}')
        plan=array(p,P+"front/plan")
        require(plan.ndim==2 and plan.shape[1]==8 and np.array_equal(plan,np.tile(np.arange(1,9),(plan.shape[0],1))),
                "single-bank plan differs from fixed 8 numerical segments")
        C=array(p,P+"front/C_f");groups=array(p,P+"front/group_C_f");cp=array(p,P+"front/Cp_f").ravel()
        require(C.shape==(18,38) and groups.shape==(18,3) and cp.shape==(18,),"wrong FE geometry shapes")
        require(np.all(C[:,:37]>0) and np.all(C[:,37]==0),"invalid/disconnected FE C")
        require(np.array_equal(C,np.tile(C[0,:],(18,1))),"numerical segments are not fully correlated")
        calculated_groups=np.column_stack((np.sum(C[:,:33],axis=1),np.sum(C[:,33:37],axis=1),C[:,37]))
        close(groups,calculated_groups,"FE grouped C",rtol=2e-15,atol=1e-28)
        require(np.all(cp==100e-15/8),"front Cp differs from declared 100 fF/half")
        cs=float(np.sum(groups[:8,0]));ctop=float(np.sum(groups[:8,:])+np.sum(cp[:8]))
        close(scalar(a,A+"Csignal_half_f"),cs,"actual signal C",rtol=3e-15)
        close(scalar(a,A+"Ctop_half_f"),ctop,"actual Ctop",rtol=3e-15)
        close(scalar(p,P+"backend/dac_coupling/fixed_single_bank_ctop_f"),ctop,"bound Ctop",rtol=3e-15)
        u=scalar(p,P+"front/unit_cap_f");weights=np.array([16]+[32]*31+[16,8,4,2,1],float)
        require(weights.size==37 and np.sum(weights)==1039,"weight geometry unexpected")
        sigma_unit=scalar(a,A+"unit_relative_sigma")
        close(sigma_unit,0.005/math.sqrt(54),"unit mismatch sigma")
        rel=array(a,A+"branch_relative_error").ravel()
        require(rel.size==37,"mismatch offsets missing")
        close(C[0,:37],u*weights*(1+rel),"physical cap draw",rtol=2e-15,atol=1e-29)
        require(int(scalar(a,A+"chip_seed"))==20261104,"chip seed differs")
        require(scalar(p,P+"front/mismatch_enabled")==1,"FE actual C not selected")
        temp=scalar(p,P+"front/temperature_K");close(temp,298.15,"temperature")
        require(scalar(p,P+"front/ktc_enabled")==1,"sample noise off")
        require(int(scalar(p,P+"front/ktc_seed"))==20261027 and
                int(scalar(a,A+"sample_ktc_seed"))==20261027,"sample kTC seed differs")
        ktc=math.sqrt(2*1.380649e-23*temp/cs)
        close(scalar(a,A+"equilibrium_ktc_diff_rms_v"),ktc,"equilibrium input kTC")
        tau_s=array(p,P+"front/tau_sample_s").ravel();tau_d=array(p,P+"front/tau_dac_s").ravel()
        close(tau_s,20*ctop,"sample RC",rtol=3e-15)
        close(tau_d,0.5e-9,"DAC tau",rtol=1e-14)
        require(np.all(array(p,P+"front/tau_precharge_s")==0),"precharge must be ideal")
        require(scalar(p,P+"backend/dac_coupling/enabled")==1,"finite DAC coupling off")
        close(scalar(a,A+"acquisition_window_s"),108e-9,"acquisition window")
        require(scalar(p,P+"backend/ni/az")==1 and get(p,P+"backend/az/mode")=="ordinary",
                "ordinary AZ not enabled")
        require(get(p,P+"digital/az_mode")=="ordinary","AZ digital mode mismatch")
        close(scalar(p,P+"backend/ra/vos_input_v"),1e-3,"RA Vos")
        close(array(p,P+"backend/az/write_tau_s"),1e-9,"AZ write tau")
        close(array(p,P+"backend/az/leak_tau_s"),10e-3,"AZ leak tau")
        require(np.all(array(p,P+"backend/az/sense_injection_half_v")==0),"unexpected AZ sense perturbation")
        Cf=scalar(p,P+"backend/ra/Cf_f");a0=scalar(p,P+"backend/ra/A0")
        ugb=scalar(p,P+"backend/ra/UGB_hz")
        close(Cf,0.864e-12,"Cf");close(a0,1e4,"A0");close(ugb,1.2e9,"UGB")
        ng=1+ctop/Cf;f=a0/(a0+ng);tau_ra=ng/(2*math.pi*ugb)
        close(scalar(a,A+"noise_gain"),ng,"actual NG")
        close(scalar(a,A+"ra_tau_s"),tau_ra,"actual RA tau")
        gm=2*175e-6*15;en=math.sqrt(8*(2/3)*1.380649e-23*temp/gm)
        sig_ra=en*f*ng*math.sqrt(1/(4*tau_ra))
        close(scalar(a,A+"A1_en_v_per_sqrt_hz"),en,"input PSD")
        close(scalar(a,A+"ra_sigma_vx_rms"),sig_ra,"assumed RA sigma")
        close(scalar(p,P+"backend/ra_noise/sigma_vx_rms"),sig_ra,"applied RA sigma")
        require(scalar(p,P+"backend/ni/ra_noise")==1,"RA OU off")
        require(int(scalar(p,P+"backend/ra_noise/seed_u64"))==20261104 and
                int(scalar(a,A+"ra_noise_seed_u64"))==20261104,
                "RA seed provenance mismatch")
        comp=P+"control/comparator/"
        require(scalar(p,comp+"enabled")==1,"comparator noise off")
        sig_cmp=math.sqrt(2*1.380649e-23*temp/100e-15)
        close(scalar(p,comp+"sar2_noise_rms_v"),sig_cmp,"comparator sigma")
        close(scalar(a,A+"cmp_sigma_vy_rms"),sig_cmp,"comparator assumption")
        require(int(scalar(p,comp+"seed_u64"))==20261105 and
                int(scalar(a,A+"cmp_noise_seed_u64"))==20261105,"comparator seed differs")
        require(scalar(p,comp+"sar2_offset_v")==0 and scalar(p,comp+"sar1_offset_v")==0
                and scalar(p,comp+"sar1_noise_rms_v")==0,"unexpected SAR1 or comparator offsets")
        scope=P+"ni/comparator_noise_scope/"
        require(scalar(p,scope+"sar1_fine")==0 and scalar(p,scope+"sar2_and_tracking")==1
                and scalar(p,scope+"flash_preconvert")==0,"comparator scope incorrect")
        require(scalar(p,P+"control/sar1/coarse_noise_rms_v")==0 and
                scalar(p,P+"control/sar1/coarse_offset_v")==0,"Flash noise or offset unexpectedly active")
        net=P+"backend/ct/"
        close(scalar(p,net+"reference_v"),1.8,"CT reference")
        main=array(p,net+"net_actual/cinc_f").ravel()
        replica=array(p,net+"net_replica/cinc_f").ravel()
        nominal=array(p,net+"net_nominal/cinc_f").ravel()
        close(nominal,900e-15,"nominal CINC");close(main,900.075e-15,"main CINC");close(replica,899.925e-15,"replica CINC")
        require(scalar(p,P+"backend/ni/cap_mismatch")==1 and scalar(p,P+"backend/ni/cinc_kick")==1
                and scalar(p,net+"replica_enabled")==1,"CT selected network or kick off")
        close(array(p,net+"output_parasitic_half_f"),0.5e-12,"RA kick output load")
        require(math.isinf(scalar(p,P+"backend/ra/slew_v_per_s")),"finite slew unexpectedly on")
        for key in ("front/dem_enabled","front/dither_enabled","front/jitter/enabled",
                    "transport/enabled","training/enabled","cal_cfg/enabled","frozen/enabled","bank/enabled",
                    "backend/ni/az_noise","backend/ni/reference_noise","backend/ni/nonlinear_ra",
                    "backend/ni/replica_delay","ni/reference_recovery"):
            require(scalar(p,P+key)==0,f"unexpected active feature {key}")
        for key in ("sample_ktc","sample_settling","dac_settling","ra_noise","comparator_noise","az","cap_mismatch"):
            require(scalar(p,P+"ni/"+key)==1,f"coverage summary mismatch: {key}")
        enbw=1/(4*tau_ra);rho=math.exp(-1.25e-9/tau_ra)
        seedk=int(scalar(p,P+"front/ktc_seed"));seedra=int(scalar(p,P+"backend/ra_noise/seed_u64"));seedcmp=int(scalar(p,comp+"seed_u64"))
        rows=[
          ("输入与几何","已实现单阵列；FSR10由独立范围配置派生",
           f"5 MS/s；N=8；FSR=10 V；Fin=97.65625 kHz；峰值 {scalar(p,P+'input/amplitude_v'):.9g} V；Cf={Cf*1e15:.6g} fF",
           "10 V范围函数门通过；5Vp的差分口径仍是假设；本 P 尚无模型执行证据。"),
          ("采集／guard","单阵列同一状态先release再采集",
           f"guard={scalar(p,P+'front/single_guard_s')*1e9:.6g} ns；采集窗108 ns；τsample={tau_s[0]*1e9:.9g} ns",
           "有限RC+kT/C函数门；本组合与2 ns guard尚非整图扫描。"),
          ("采样 kT/C","单bank有限RC随机创新与历史状态",
           f"ON；T={temp:.2f} K；seed={seedk}；实际信号C={cs*1e12:.9g} pF/half；平衡近似σ={ktc*1e6:.9g} µV rms",
           f"函数门 {gate_n} 点：归一方差={gate_var:.5g}、lag-1={gate_lag:.5g}（理论{gate_lag_ref:.5g}）；非此P的统计或PDK证明。"),
          ("一级C固定失配","显式实际C参与模拟电荷；不输入数字权重",
           f"ON；σunit假设={sigma_unit*100:.7g}%；seed=20261104；8个数值段逐列一致，38列=0",
           "只准备一颗假设芯片；没有此profile多chip/梯度/PN独立失配扫描。"),
          ("前端／RA负载寄生","前端Cp计入Ctop；RA输出负载进入kick分母",
           f"前端Cp={np.sum(cp[:8])*1e15:.6g} fF/half；RA输出={array(p,net+'output_parasitic_half_f').ravel()[0]*1e12:.6g} pF/half；Ctop={ctop*1e12:.9g} pF/half",
           "两个数均为未提取假设；输出负载不是完整RA负载极点。"),
          ("DAC有限建立","旧FE状态驱动RA解析耦合",
           f"ON；τDAC={tau_d[0]*1e9:.6g} ns；coupling=true",
           "OU+AZ+finiteDAC函数门；并非该联合P的整图或工艺扫描。"),
          ("RA有限增益、带宽与失调","单极点、有限A0及输入差分Vos",
           f"A0={a0:g}；UGB={ugb/1e9:.6g} GHz；NG={ng:.9g}；τ={tau_ra*1e9:.9g} ns；Vos=+1 mV",
           "有限参数及Vos为设计假设；非电路辨识；1mV普通AZ曾作另一个N8对照。"),
          ("普通 AZ","输入参考有限写入与保持；无随机AZ噪声",
           "ordinary ON；write τ=1 ns；leak τ=10 ms；sense扰动=0",
           "普通AZ在旧条件有N8；本P的10 ms保持未单独扫描；不证明1/f或3级环放。"),
          ("RA OU噪声","固定极点带限OU；事件键重复确定",
           f"ON；σVX={sig_ra*1e3:.9g} mV rms；seed={seedra}；假设ENBW={enbw/1e6:.6g} MHz、1.25 ns相关系数≈{rho:.6g}",
           "A1通道热噪声代理；联合函数门通过；不等于全部RA噪声或本P PSD验证。"),
          ("二级/TA比较器","已实现VY输入参考、逐决策噪声候选",
           f"ON；σVY={sig_cmp*1e3:.9g} mV rms；seed={seedcmp}；固定offset=0未注入",
           "比较器函数门；sigma来自假设100 fF等效噪声电容，不是再生锁存器实测。"),
          ("一级细／Flash比较器","无该配置噪声覆盖；Flash随机噪声未实现",
           "SAR1细noise=0、offset=0；粗Flash noise=0、offset=0",
           "关闭或未实现，不能因SAR2噪声开启而计入。"),
          ("CT CINC与replica","主/副独立网络及反馈kick路径",
           f"ON；名义900 fF；主={main[0]*1e15:.9g} fF，副={replica[0]*1e15:.9g} fF/half",
           "确定性一σ配对示例；其他CT电容名义；无此normal P的实测非零kick/扫描。"),
          ("参考与驱动噪声","固定参考源；恢复/噪声无当前实现",
           f"前端Vref={scalar(p,P+'front/vref_v'):.6g} V；CT Vref={scalar(p,net+'reference_v'):.6g} V；随机参考噪声OFF",
           "动态参考恢复/噪声和驱动噪声未建；标称设置不等于测得误差为0。"),
          ("孔径/全时钟jitter","有限RC+jitter联合未获资格",
           "OFF；0.5 ps是单独预算，不在本P启用",
           "不算覆盖；不把旧25 ps压力案迁移到正常点。"),
          ("RA slew／非线性","有限slew近似在其他条件有代码，联合有限DAC未获资格",
           "slew=+Inf；非线性RA OFF",
           "不是有限slew覆盖；没有晶体管动态和FIA储能模型。"),
          ("数字校准／传输","名义权重、直接RAW",
           "training、frozen、Bank、transport、DEM、dither均OFF",
           "论文芯片采用片外LMS；当前不应称已复现校准结果。"),
          ("tracking","固定M8日历与SINC²名义重构",
           "准备为12次D2、8次TA比较、7次反馈",
           "该P尚无实际事件/反馈观测；不把理论9dB或论文7dB当已验证收益。"),
        ]
    context=f"""# 正常工作点：非理想三态核对

本表读取**实际 prepare 保存的 P**，并核对原始回执、假设、源码及5项函数门；这是参数和函数级证据。尚未由本脚本证明该P在Simulink主图执行、获得8个有效码、扫描性能或通过工艺验证。所有数值均为本次行为配置及其明确假设，不是PDK/论文标称。

| 模块 | 已实现的范围 | 此次实际准备参数 | 已验证／已扫描的边界 |
|---|---|---|---|
"""
    for cells in rows:
        context+="| "+" | ".join(str(v).replace("|","/") for v in cells)+" |\n"
    status_links="、".join(mdlink("执行状态",p) for p in status_paths)
    context+=f"""
真实参数：[normal_P.mat](<{profile/'normal_P.mat'}>)（SHA-256 {receipt['normal_P_sha256']}）；[assumptions.mat](<{profile/'assumptions.mat'}>)（SHA-256 {receipt['assumptions_sha256']}）；[profile回执](<{profile/'complete.json'}>)。五项函数门的 [采样RC+kT/C](<{gate_evidence['test_single_rc_ktc']}>)、[OU+AZ+DAC](<{gate_evidence['test_joint_ou_az_dac']}>)、[合并返回](<{gate_evidence['test_joint_ou_rc_return']}>)、[比较器](<{gate_evidence['test_comparator_single']}>) 和 [10 V范围](<{gate_evidence['test_normal_10v']}>) 使用同一冻结候选源码清单；函数门不代表五类非理想组合在主图的结果。

完整阶段还核对了控制器中先经零退出和后验校验再追加的 completed 记录：{status_links}；某批次后续阶段失败不撤销其 completed 中的先前阶段。独立检查了P/assumptions哈希、11个与物理路径有关的磁盘源码字节、完整五门回执与报告哈希、实际C矩阵及8段相关性、CT与RA参数、噪声公式和零/Inf/关闭项；这不单独证明所有MATLAB传递依赖的动态which或缓存字节。离线审计未运行MATLAB；本normal P尚无参数扫描、PSD、全范围静态线性、PDK或电路级结论。前端信号C和Cp的半阵解释、等效RC与各噪声/匹配参数均按来源说明保留假设标签。
"""
    with out.open("x",encoding="utf-8") as f:
        f.write(context)
    print(f"created {out}")
    print(f"sha256 {sha(out)}")
    print(f"actual Csignal={cs:.17g} F, Ctop={ctop:.17g} F, tau_sample={tau_s[0]:.17g} s, sigma_vx={sig_ra:.17g} V")

if __name__=="__main__":
    main()

