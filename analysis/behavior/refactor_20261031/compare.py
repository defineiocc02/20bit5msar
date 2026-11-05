import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
print(f"cases: before={len(a)} after={len(b)}")
ok=True
for i,(x,y) in enumerate(zip(a,b)):
    if x.get('status')!='ok' or y.get('status')!='ok':
        print(f"  case {i}: STATUS before={x.get('status')} after={y.get('status')}")
        ok=False; continue
    keys=set(x)|set(y)
    diffs=[]
    for k in sorted(keys):
        if k=='status': continue
        if x.get(k)!=y.get(k):
            diffs.append(k)
    if diffs:
        ok=False
        print(f"  case {i}: {len(diffs)} DIFF -> {diffs[:6]}")
        for k in diffs[:3]:
            print(f"      {k}:\n        before={str(x.get(k))[:90]}\n        after ={str(y.get(k))[:90]}")
    else:
        print(f"  case {i}: IDENTICAL ({len(keys)-1} fields)")
print()
print("RESULT:", "PASS - behaviour identical" if ok else "FAIL - differences found")
sys.exit(0 if ok else 1)
