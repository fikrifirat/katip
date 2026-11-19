# Dev/test split for the external sets (sha256 of "split20261119:<doc id>", even = dev). Rules were changed
# only from errors read on the dev half; this prints F2, recall, precision, leak and a paired bootstrap
# (2,000 resamples) against newmind-kvkk-v2 per set.  python heldout.py base-v4,newmind-kvkk-v2 test|dev|unseen
import sys, json, hashlib, numpy as np
sys.path.insert(0,'/home/user/katip/lab/legal/external')
import ext_bench as E, re
def tmpl(d):
    t=d['text']; out=[]; last=0
    for a,b,l in sorted(d['spans']): out.append(t[last:a]); out.append('<'+l+'>'); last=max(last,b)
    out.append(t[last:]); return re.sub(r'\d','0',re.sub(r'\s+',' ',''.join(out).lower()))
dev = lambda i: int(hashlib.sha256(("split20261119:"+str(i)).encode()).hexdigest(),16)%2==0
keys=sys.argv[1].split(','); half=sys.argv[2]
SUB={"nm6k":None,"werea":None,"cagri":"cagri-tam","piimask":"piimask-tr"}
rng=np.random.default_rng(20261119); out={}
for s,sub in SUB.items():
    ALL=E.load(s); seen={tmpl(d) for d in ALL if dev(d['id'])}
    docs=[d for d in ALL if (dev(d['id'])==(half=='dev')) and (sub is None or d['track']==sub) and (half!='unseen' or tmpl(d) not in seen)]
    if not docs: continue
    neg=[d for d in E.load(s) if (dev(d['id'])==(half=='dev')) and d['track']=='cagri-negatif' and (half!='unseen' or tmpl(d) not in seen)]
    C={}
    for k in keys:
        P={json.loads(l)['id']:json.loads(l)['spans'] for l in open(f'preds/{k}__{s}.jsonl')}
        C[k]=[E._doc_counts(d,P.get(d['id'],[]),E.MAP[s]) for d in docs]
        a=E._agg(C[k]); row=f"{s:8} {half} n={len(docs):3} {k:18} F2 {100*a['f2']:5.1f} R {100*a['recall']:5.1f} P {100*a['precision']:5.1f} leak {100*a['leak_core']:5.1f}"
        if neg: row+=f"  neg-false/1k {E._agg([E._doc_counts(d,P.get(d['id'],[]),E.MAP[s]) for d in neg])['false_masks_per_1k_words']:.1f}"
        if k!='newmind-kvkk-v2':
            ref=C.get('newmind-kvkk-v2') or [E._doc_counts(d,{json.loads(l)['id']:json.loads(l)['spans'] for l in open(f'preds/newmind-kvkk-v2__{s}.jsonl')}.get(d['id'],[]),E.MAP[s]) for d in docs]
            n=len(docs); diffs=[]
            for _ in range(2000):
                ix=rng.integers(0,n,n); diffs.append(E._agg([C[k][i] for i in ix])['f2']-E._agg([ref[i] for i in ix])['f2'])
            lo,hi=np.percentile(diffs,[2.5,97.5]); row+=f"  vs NewMind [{100*lo:+.1f}, {100*hi:+.1f}]"
        print(row)
