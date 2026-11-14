"""Sentence-clustered bootstrap CIs and paired tests for the KVKK-Bench paper.

  # in a checkout of the legal-study branch, after `python lab/foreign/build.py && python lab/legal/bench_build.py`
  python paper/bootstrap_ci.py 10000 .      # prints Table 1 CIs and paired differences; writes paper/bootstrap_samples.json
"""
import json,glob,sys,random
import numpy as np
ROOT=sys.argv[2] if len(sys.argv)>2 else '.'
sys.path[:0]=[ROOT+'/lab/legal']
import bench_score as S, bench_build as B
D=ROOT+'/lab/data/bench/v0.1.2/public/'
TR=['court-turkish','court-foreign','prose']; W={'court-turkish':25,'court-foreign':10,'prose':10}
gold={t:B.load(D+t+'.jsonl') for t in TR}
SYS=['berturk-v2','xlmr-conll','akdeniz','gliner2-pii','savasy','gliner','tiny-f','cosmos-pii','qwen-1.5b','openmed-pf-v2','openai-pf','piiranha','presidio','openmed-tr-33m']
def key(t,g): return g['id'].split('-',2)[2].split('#')[0] if t!='prose' else g['id']
# cluster index: court sentences shared across the two court tracks
clusters={}
for t in TR:
    for g in gold[t]: clusters.setdefault(('court' if t!='prose' else 'prose', key(t,g)),[]).append((t,g))
court_cl=[k for k in clusters if k[0]=='court']; prose_cl=[k for k in clusters if k[0]=='prose']
print(len(court_cl),len(prose_cl))
def counts(g,ps):
    text=g['text']; masked=np.zeros(len(text),bool)
    for s,e,_ in ps: masked[max(0,s):min(len(text),e)]=True
    G=F=Sx=T=0; gc=lc=0
    for s,e,ty in g['spans']:
        if ty!='PERSON': continue
        G+=1; F+=any(pt=='PERSON' and S.matches(text[a:b],text[s:e]) for a,b,pt in ps)
        gc+=e-s; lc+=int((~masked[s:e]).sum())
    gs=[(s,e) for s,e,ty in g['spans'] if ty=='PERSON']
    for a,b,pt in ps:
        if pt=='PERSON': Sx+=1; T+=S.true_span(text,a,b,gs)
    return np.array([G,F,Sx,T,gc,lc],float)
f2=lambda p,r:5*p*r/(4*p+r) if p+r else 0.0
C={}
for k in SYS:
    P={d['id']:d['spans'] for d in map(json.loads,open(ROOT+f'/lab/legal/bench/preds/{k}.jsonl'))}
    C[k]={cl:{t:sum(counts(g,P.get(g['id'],[])) for (tt,g) in clusters[cl] if tt==t) for t in TR if any(tt==t for tt,_ in clusters[cl])} for cl in clusters}
def stat(k,sample):
    agg={t:np.zeros(6) for t in TR}
    for cl in sample:
        for t,v in C[k][cl].items(): agg[t]+=v
    dims={}; leaks=[]
    for t in TR:
        G,F,Sx,T,gc,lc=agg[t]; r=F/G; p=T/Sx if Sx else 0; dims[t]=f2(p,r); leaks.append(lc/gc)
    ov=sum(W[t]*dims[t] for t in TR)/sum(W.values())
    return ov,float(np.mean(leaks)),dims['court-turkish'],dims['court-foreign'],dims['prose']
allcl=list(clusters)
point={k:stat(k,allcl) for k in SYS}
for k in SYS: print(k,[round(100*x,1) for x in point[k]])
N=int(sys.argv[1]); rng=random.Random(20261114)
samp={k:[] for k in SYS}
for i in range(N):
    s=[rng.choice(court_cl) for _ in court_cl]+[rng.choice(prose_cl) for _ in prose_cl]
    for k in SYS: samp[k].append(stat(k,s))
json.dump({'N':N,'point':point,'samp':samp},open('paper/bootstrap_samples.json','w'))
def ci(xs): xs=sorted(xs); return xs[int(.025*len(xs))], xs[int(np.ceil(.975*len(xs)))-1]
print('SYSTEM overall [CI] leak [CI] tr fo ev')
for k in SYS:
    o=[x[0] for x in samp[k]]; l=[x[1] for x in samp[k]]
    print(f"{k:15} {100*point[k][0]:.1f} [{100*ci(o)[0]:.1f}, {100*ci(o)[1]:.1f}]  leak {100*point[k][1]:.1f} [{100*ci(l)[0]:.1f}, {100*ci(l)[1]:.1f}]")
print('PAIRED vs Base: dOverall [CI] p_two_sided ; dLeak [CI]')
b=samp['berturk-v2']
for k in SYS[1:]:
    d=[x[0]-y[0] for x,y in zip(b,samp[k])]; dl=[x[1]-y[1] for x,y in zip(b,samp[k])]
    p=2*min(sum(v<=0 for v in d),sum(v>=0 for v in d))/N
    pl=2*min(sum(v<=0 for v in dl),sum(v>=0 for v in dl))/N
    print(f"{k:15} d={100*(point['berturk-v2'][0]-point[k][0]):+.1f} [{100*ci(d)[0]:+.1f}, {100*ci(d)[1]:+.1f}] p={min(1,p):.3f} ; dLeak {100*(point['berturk-v2'][1]-point[k][1]):+.1f} [{100*ci(dl)[0]:+.1f}, {100*ci(dl)[1]:+.1f}] p={min(1,pl):.3f}")
