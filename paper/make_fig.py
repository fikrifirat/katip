import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
B=json.load(open('paper/bootstrap_samples.json'))
R={s:json.load(open(f'lab/legal/bench/results/{s}.json')) for s in B['point']}
NAME={'berturk-v2':'Katip Mask Base','tiny-f':'Katip Mask Nano','xlmr-conll':'XLM-R Large (CoNLL)','akdeniz':'XLM-R Base TR NER',
'gliner2-pii':'GLiNER2 PII','savasy':'BERTurk NER','gliner':'GLiNER multi PII','cosmos-pii':'ModernBERT-TR PII','qwen-1.5b':'Qwen2.5-1.5B',
'openmed-pf-v2':'OpenMed PF v2','openai-pf':'OpenAI Privacy Filter','piiranha':'Piiranha','presidio':'Presidio+spaCy','openmed-tr-33m':'OpenMed TR 33M'}
plt.rcParams.update({'font.size':7.5,'font.family':'serif','axes.edgecolor':'#52514e','axes.labelcolor':'#0b0b0b','xtick.color':'#52514e','ytick.color':'#52514e'})
fig,ax=plt.subplots(figsize=(3.3,2.5))
for s,p in B['point'].items():
    o=sorted(x[0] for x in B['samp'][s]); lo,hi=o[int(.025*len(o))],o[int(.975*len(o))-1]
    size=R[s]['size_mb'] or 11.0; y=100*p[0]; katip=s in('berturk-v2','tiny-f')
    c='#2a78d6' if katip else '#8a8984'
    ax.errorbar(size,y,yerr=[[y-100*lo],[100*hi-y]],fmt='o',ms=4.2 if katip else 3.2,color=c,mec='#fcfcfb',mew=.8,elinewidth=.9,capsize=0,zorder=3 if katip else 2)
    pos={'berturk-v2':(85,97.0,'right',False),'tiny-f':(4,86.3,'left',False),'savasy':(330,91.6,'right',False),'cosmos-pii':(400,80.5,'right',False),
         'presidio':(14,45,'left',False),'openmed-tr-33m':(170,19.1,'left',False),
         'xlmr-conll':(13000,99.5,'left',True),'akdeniz':(13000,95.5,'left',True),'gliner2-pii':(13000,91.5,'left',True),'gliner':(13000,87.5,'left',True),
         'qwen-1.5b':(13000,62,'left',True),'openmed-pf-v2':(13000,57,'left',True),'openai-pf':(13000,52,'left',True),'piiranha':(13000,47,'left',True)}
    tx,ty,ha,arrow=pos[s]
    ax.annotate(NAME[s],(size,y),xytext=(tx,ty),fontsize=5.8,ha=ha,va='center',color='#0b0b0b' if katip else '#52514e',fontweight='bold' if katip else 'normal',annotation_clip=False,
                arrowprops=dict(arrowstyle='-',color='#b5b4ae',lw=.5,shrinkA=1,shrinkB=3) if arrow else None)

ax.set_xscale('log'); ax.set_xlim(1.5,1.2e4); ax.set_ylim(10,102)
ax.set_xlabel('Download size (MB, log scale)'); ax.set_ylabel('Overall (real text, 0–100)')
ax.grid(True,which='major',color='#e4e3df',lw=.5); ax.set_axisbelow(True)
for sp in ('top','right'): ax.spines[sp].set_visible(False)
fig.tight_layout(pad=0.3); fig.subplots_adjust(right=0.70); fig.savefig('paper/fig_overall_size.pdf')
