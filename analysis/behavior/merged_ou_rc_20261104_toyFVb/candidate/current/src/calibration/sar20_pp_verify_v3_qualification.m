function sar20_pp_verify_v3_qualification(q,Q)
%SAR20_PP_VERIFY_V3_QUALIFICATION Trusted adapter to frozen v3 LOAD/QUALIFY.
% Inputs q and Q contain only reviewed hashes/public cfg/plan/h. No holdout
% rows, references, full P or analog truth. These are compile-time virtual
% transactions, not extra Simulink events or an activated bank.
    paths={'sar20_bank_owner_init','sar20_bank_owner_step','sar20_bank_certificate_sha256','sar20_bank_sha256'};
    pins={'0d45e683ed7c3d04ea91181a590a83dd15e934d6f6411ac32d9d210da4eac0ca', ...
          '6e3987cbd67f62bac1b176bff4298660e2464284f4104c7aa53d794d0b827b2d', ...
          '951f1f7f3ede5947be31b73cc7f599e6f658df69853c49646768c252db3c16a5', ...
          'd050e9f48c6762578f8297bb9b8c32761fa31157d96ce52ed31c575c32a5caea'};
    for k=1:numel(paths)
        f=which(paths{k});assert(~isempty(f)&&strcmp(file_sha(f),pins{k}), ...
            'pp:v3Source','Resolved %s is not the frozen v3 source.',paths{k});
    end
    profile=struct('schema','sar20-bank-profile/v1','chip_id','registered_behavior_chip_20261028', ...
        'profile_id','rx_m8_tau0_predeclared','tau_dac_s',zeros(18,1));
    profileSha=sar20_bank_sha256(unicode2native(jsonencode(orderfields(profile)),'UTF-8'));
    train=cell(2,1);qual=cell(2,1);ta=cell(2,1);qa=cell(2,1);
    for k=1:2
        common=struct('schema','sar20-bank-train-certificate/v1','kind','registered', ...
            'status','trained','version',q.versions(k),'chip_id',profile.chip_id,'profile_id',profile.profile_id, ...
            'profile_sha256',profileSha,'coefficient_sha256',Q.coefficient_sha256, ...
            'public_cfg_sha256',Q.public_cfg_sha256,'plan_sha256',Q.plan_sha256, ...
            'protocol_sha256',Q.protocol_sha256,'acceptance','NOT_ACCEPTED','activation','none');
        train{k}=common;train{k}.training_receipt_sha256=Q.training_receipt_sha256;
        train{k}.freeze_receipt_sha256=Q.freeze_receipt_sha256;
        train{k}.coefficient_file_sha256=Q.coefficient_file_sha256;
        ta{k}=sar20_bank_certificate_sha256(train{k});
        common.schema='sar20-bank-qualification-certificate/v1';common.status='passed';
        qual{k}=common;qual{k}.training_certificate_sha256=ta{k};
        qual{k}.evaluation_receipt_sha256=Q.evaluation_receipt_sha256;
        qual{k}.holdout_result_sha256=Q.public_holdout_result_sha256;
        qa{k}=sar20_bank_certificate_sha256(qual{k});
    end
    authority=struct('mode','registered','approved_training_sha256',{ta}, ...
        'approved_qualification_sha256',{qa},'approved_drain_sha256',{{}});
    S=sar20_bank_owner_init(q.slot{1}.public_cfg,q.slot{1}.plan,profile,authority,q.epoch,0,q.lead_samples);
    for k=1:2
        E=event(2*k-2,struct('op','load','command_id',2*k-1,'slot',k, ...
            'version',q.versions(k),'cache',q.slot{k},'certificate',train{k}));
        [S,O]=sar20_bank_owner_step(S,E);
        assert(strcmp(O.command_status,'LOADED_CANDIDATE_NOT_QUALIFIED')&&~O.code_valid, ...
            'pp:v3Load','Frozen v3 refused public training/freeze identity.');
        E=event(2*k-1,struct('op','qualify','command_id',2*k,'slot',k, ...
            'version',q.versions(k),'certificate',qual{k}));
        [S,O]=sar20_bank_owner_step(S,E);
        assert(strcmp(O.command_status,'QUALIFIED_NOT_ACTIVE')&&~O.code_valid&& ...
            strcmp(S.slots(k).state,'qualified')&&isequal(S.slots(k).h,q.slot{k}.h), ...
            'pp:v3Qualify','Frozen v3 refused independent holdout identity.');
    end
end
function E=event(hit,cmd)
    E=struct('hit',hit,'raw_ready',0,'raw6',nan(6,1),'nominal_code',NaN,'rx_fault',0,'command',cmd);
end
function h=file_sha(p)
    f=fopen(p,'rb');assert(f>=0,'pp:file','Cannot read frozen v3 source.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    md=java.security.MessageDigest.getInstance('SHA-256');while ~feof(f),md.update(fread(f,1048576,'*uint8'));end
    h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
