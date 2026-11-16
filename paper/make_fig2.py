# Figures 2-3: leak vs speed, and per-track F2 with 95% CIs. Run from the repo root on legal-study
# (needs lab/legal/bench/results and paper/bootstrap_samples.json from bootstrap_ci.py).
import json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
B=json.load(open('paper/bootstrap_samples.json'))
R={s:json.load(open(f'lab/legal/bench/results/{s}.json')) for s in B['point']}
NAME={'berturk-v2':'Katip Mask Base','mini-v2':'Katip Mask Mini','tiny-f':'Katip Mask Nano','xlmr-conll':'XLM-R Large (CoNLL)','akdeniz':'XLM-R Base TR NER',
'gliner2-pii':'GLiNER2 PII','savasy':'BERTurk NER','gliner':'GLiNER multi PII','cosmos-pii':'ModernBERT-TR PII','qwen-1.5b':'Qwen2.5-1.5B',
'openmed-pf-v2':'OpenMed PF v2','openai-pf':'OpenAI Privacy Filter','piiranha':'Piiranha','presidio':'Presidio+spaCy','openmed-tr-33m':'OpenMed TR 33M'}
KATIP=('berturk-v2','mini-v2','tiny-f'); BLUE='#2a78d6'; GREY='#8a8984'
plt.rcParams.update({'font.size':7.5,'font.family':'serif','axes.edgecolor':'#52514e','axes.labelcolor':'#0b0b0b','xtick.color':'#52514e','ytick.color':'#52514e'})
def ci(s,i):
    o=sorted(x[i] for x in B['samp'][s]); return 100*o[int(.025*len(o))],100*o[int(.975*len(o))-1]
def style(ax):
    ax.grid(True,which='major',color='#e4e3df',lw=.5); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)

# Figure 2: leak rate vs pages per second (Katip speeds: the 15 Nov timing run, as Table 2)
fig,ax=plt.subplots(figsize=(3.3,2.5))
pos={'berturk-v2':(0.6,15,'right',True),'mini-v2':(14,13,'left',True),'tiny-f':(43,25.5,'center',False),'xlmr-conll':(0.6,0.5,'right',True),
     'akdeniz':(14,3.5,'left',True),'gliner2-pii':(0.6,5,'right',True),'savasy':(14,8,'left',True),'gliner':(0.6,10,'right',True),'cosmos-pii':(0.6,21.6,'right',True),
     'qwen-1.5b':(0.017,41,'left',False),'openmed-pf-v2':(0.21,36.4,'left',False),'openai-pf':(0.14,52.5,'left',False),'piiranha':(4,45.4,'left',False),
     'presidio':(31,37,'center',False),'openmed-tr-33m':(7.46,78.5,'center',False)}
for s,p in B['point'].items():
    sp=1000/({'berturk-v2':597.0,'mini-v2':198.0,'tiny-f':23.0}.get(s) or R[s]['ms_per_page']); y=100*p[1]; lo,hi=ci(s,1); k=s in KATIP
    ax.errorbar(sp,y,yerr=[[y-lo],[hi-y]],fmt='o',ms=4.2 if k else 3.2,color=BLUE if k else GREY,mec='#fcfcfb',mew=.8,elinewidth=.9,capsize=0,zorder=3 if k else 2)
    tx,ty,ha,arrow=pos[s]
    ax.annotate(NAME[s],(sp,y),xytext=(tx,ty),fontsize=5.6,ha=ha,va='center',color='#0b0b0b' if k else '#52514e',fontweight='bold' if k else 'normal',annotation_clip=False,
                arrowprops=dict(arrowstyle='-',color='#b5b4ae',lw=.5,shrinkA=1,shrinkB=3) if arrow else None)
ax.set_xscale('log'); ax.set_xlim(0.005,150); ax.set_ylim(-5,82); ax.invert_yaxis()
ax.set_xlabel('Pages per second (one laptop CPU, log scale)'); ax.set_ylabel('Leak rate (%), lower is better')
style(ax); fig.tight_layout(pad=0.3); fig.savefig('paper/fig_leak_speed.pdf')

# Figure 3: per-track F2 with 95% CIs, top systems
SYS=['berturk-v2','mini-v2','tiny-f','xlmr-conll','akdeniz','gliner2-pii','savasy','cosmos-pii']
TR=[(2,'Court text,\nTurkish names'),(3,'Court text,\nforeign names'),(4,'Everyday text\n(Wikipedia)')]
fig,axs=plt.subplots(1,3,figsize=(6.9,1.95),sharey=True)
for ax,(i,t) in zip(axs,TR):
    for j,s in enumerate(SYS):
        y=len(SYS)-1-j; x=100*B['point'][s][i]; lo,hi=ci(s,i); k=s in KATIP
        ax.plot([lo,hi],[y,y],color=BLUE if k else GREY,lw=1.4,solid_capstyle='round')
        ax.plot(x,y,'o',ms=4.2 if k else 3.4,color=BLUE if k else GREY,mec='#fcfcfb',mew=.8)
        ax.text(hi+(1.2 if i<4 else 2.5),y,f'{x:.1f}',va='center',fontsize=5.6,color='#52514e')
    ax.set_title(t,fontsize=7); style(ax); ax.grid(False,axis='y')
    lo_all=min(ci(s,i)[0] for s in SYS); ax.set_xlim(max(0,lo_all-4),104)
axs[0].set_yticks(range(len(SYS))); axs[0].set_yticklabels([NAME[s] for s in reversed(SYS)])
for lab in axs[0].get_yticklabels():
    if lab.get_text().startswith('Katip'): lab.set_fontweight('bold'); lab.set_color('#0b0b0b')
axs[1].set_xlabel('F2 (recall-weighted), 95% CI')
fig.tight_layout(pad=0.3,w_pad=0.8); fig.savefig('paper/fig_tracks.pdf')
