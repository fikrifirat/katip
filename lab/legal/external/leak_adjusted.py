# Held-out test halves: leak-rate difference with a paired bootstrap, and piimask rescored with a documented
# gold adjustment (unlabelled repeat mentions of a labelled person's name added as PERSON). python leak_adjusted.py
import sys, json, hashlib, re, numpy as np
sys.path.insert(0,'/home/user/katip/lab/legal/external')
import ext_bench as E
dev = lambda i: int(hashlib.sha256(("split20261119:"+str(i)).encode()).hexdigest(),16)%2==0
SUB={"nm6k":None,"werea":None,"cagri":"cagri-tam","piimask":"piimask-tr"}
W=re.compile(r"[A-ZÇĞİÖŞÜ][a-zçğıöşü]+")
def adjust(d, mp):
    """Repeat-mention rule: an unlabelled capitalised word equal to a word of a gold PERSON value in the same
    document becomes a PERSON gold value too ("Cem Sönmez ... Sönmez, telefonunu")."""
    t=d['text']; pl=[l for l,ty in mp.items() if ty=='PERSON']
    words={w for a,b,l in d['spans'] if l in pl for w in W.findall(t[a:b])}
    sp=list(d['spans']); add=0
    for m in W.finditer(t):
        if m.group() in words and not any(a<m.end() and m.start()<b for a,b,_ in sp):
            sp.append([m.start(),m.end(),pl[0]]); add+=1
    return {**d,'spans':sp}, add
def boot(a,b,key,n=2000,seed=20261119):
    rng=np.random.default_rng(seed); N=len(a); out=[]
    for _ in range(n):
        ix=rng.integers(0,N,N); out.append(E._agg([a[i] for i in ix])[key]-E._agg([b[i] for i in ix])[key])
    return np.percentile(out,[2.5,97.5])
for s,sub in SUB.items():
    docs=[d for d in E.load(s) if not dev(d['id']) and (sub is None or d['track']==sub)]
    P={k:{json.loads(l)['id']:json.loads(l)['spans'] for l in open(f'preds/{k}__{s}.jsonl')} for k in ('base-v4','newmind-kvkk-v2')}
    C={k:[E._doc_counts(d,P[k].get(d['id'],[]),E.MAP[s]) for d in docs] for k in P}
    lo,hi=boot(C['base-v4'],C['newmind-kvkk-v2'],'leak_core')
    A={k:E._agg(C[k]) for k in C}
    print(f"{s:8} leak Base {100*A['base-v4']['leak_core']:.1f}% NewMind {100*A['newmind-kvkk-v2']['leak_core']:.1f}%  diff CI [{100*lo:+.1f},{100*hi:+.1f}]  clean docs {100*A['base-v4']['clean_doc_rate']:.0f}% vs {100*A['newmind-kvkk-v2']['clean_doc_rate']:.0f}%")
    if s=='piimask':
        adj=[adjust(d,E.MAP[s]) for d in docs]; print('  repeat-mention gold added:',sum(x for _,x in adj),'in',sum(x>0 for _,x in adj),'docs')
        CA={k:[E._doc_counts(d,P[k].get(d['id'],[]),E.MAP[s]) for d,_ in adj] for k in P}
        for k in CA: a=E._agg(CA[k]); print(f"  adjusted {k:16} F2 {100*a['f2']:.1f} R {100*a['recall']:.1f} P {100*a['precision']:.1f}")
        lo,hi=boot(CA['base-v4'],CA['newmind-kvkk-v2'],'f2'); print(f"  adjusted F2 diff CI [{100*lo:+.1f},{100*hi:+.1f}]")
        lo,hi=boot(CA['base-v4'],CA['newmind-kvkk-v2'],'precision'); print(f"  adjusted precision diff CI [{100*lo:+.1f},{100*hi:+.1f}]")
