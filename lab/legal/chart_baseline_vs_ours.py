import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
from math import sqrt
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (c-h)*100,(c+h)*100
M=["Presidio + spaCy, off-the-shelf","Rules only (0.3 MB)","Katip Tiny, published (2.6 MB)","pii-names-tiny (2.6 MB)","DistilBERTurk + real text (68 MB)","BERTurk v1: baseline (111 MB)","BERTurk v2: ours (111 MB)"]
# (recall, lo, hi) ; None CI -> Wilson approx
blind={-1:(55.1,48.7,61.2),0:(98.4,96.4,99.7),1:(99.7,99.1,100),2:(99.5,98.6,100),3:(99.7,99.1,100),4:(100,100,100),5:(100,100,100)}
wiki={-1:(75.1,71.1,78.6),0:(15.0,11.0,19.3),1:(14.8,11.1,18.9),2:(55.5,51.2,60.1),3:(73.1,69.1,76.8),4:(40.7,35.8,45.3),5:(89.8,87.1,92.1)}
leg={-1:(46.1,43.3,48.7),0:(90.6,89.0,92.1),5:(99.3,98.9,99.7)}
for i,r in {1:93.9,2:93.5,3:98.4,4:98.6}.items():
    lo,hi=wilson(round(r/100*1643),1643); leg[i]=(r,lo,hi)
prec_leg={-1:11.6,0:96.0,1:95.9,2:83.0,3:96.1,4:95.9,5:96.2}
GREY="#a3a29c"; BASE="#eb6834"; OURS="#2a78d6"; INK="#0b0b0b"; INK2="#52514e"
col=[GREY,GREY,GREY,GREY,GREY,BASE,OURS]
panels=[("Synthetic test set\n(80 generated docs, 365 names)",blind,(0,103)),
        ("Real Wikipedia sentences\n(Wiki NER test, 654 names)",wiki,(0,103)),
        ("Real Yargıtay prose, names filled in\n(TurkishLegalNER, 1,643 names)",leg,(0,103))]
fig,axs=plt.subplots(1,3,figsize=(15,4.6),sharey=True,gridspec_kw=dict(wspace=0.08))
y=np.arange(len(M))[::-1]
for ax,(t,d,xl) in zip(axs,panels):
    for i in range(len(M)):
        r,lo,hi=d[i-1]; ax.plot([lo,hi],[y[i]]*2,color=col[i],lw=2,solid_capstyle="round")
        ax.plot(r,y[i],"o",ms=9,color=col[i],mec="white",mew=2,zorder=3,clip_on=False)
        ax.text(r,y[i]+0.28,f"{r:.1f}%",ha="center",va="bottom",fontsize=9,color=INK if i>=5 else INK2,fontweight="bold" if i>=5 else "normal")
    ax.set_xlim(*xl); ax.set_ylim(-0.5,len(M)-0.2); ax.set_title(t,fontsize=10.5,color=INK,loc="left",pad=12)
    ax.set_xticks([0,20,40,60,80,100]); ax.grid(axis="x",color="#e6e5e0",lw=0.8); ax.set_axisbelow(True)
    for s in ("top","right","left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7"); ax.tick_params(colors=INK2,labelsize=9,left=False)
    ax.set_xlabel("names found (recall), 95% CI",fontsize=9,color=INK2)
axs[0].set_yticks(y); axs[0].set_yticklabels(M,fontsize=10)
for lab,i in zip(axs[0].get_yticklabels(),range(len(M))): lab.set_color(INK if i>=5 else INK2); lab.set_fontweight("bold" if i>=5 else "normal")
ax2=axs[2]
for i in range(len(M)):
    ax2.text(106,y[i],f"prec {prec_leg[i-1]:.1f}%",va="center",fontsize=9,color=("#c0392b" if prec_leg[i-1]<95 else INK2),transform=ax2.transData,clip_on=False)
fig.suptitle("Same models, three test sets: synthetic scores hide the real-text gap",x=0.01,ha="left",fontsize=13,color=INK,fontweight="bold",y=1.10)
fig.text(0.01,1.03,"Baseline = BERTurk v1 (synthetic training only). Ours = BERTurk v2 (same model + 18k real Wikipedia sentences). Each system as Katip runs it (rules + model).",fontsize=9.5,color=INK2)
fig.text(0.01,-0.06,"Wiki and synthetic CIs: document-level bootstrap (lab/results 03, 04). Presidio CIs: document-level bootstrap (lab/baselines.py, run today). Legal CIs for v1, Tiny, pii-names-tiny and DistilBERTurk are Wilson intervals from point scores (approximate, narrower than a bootstrap). Precision ≥95% is a selection rule; red = fails it.",fontsize=8,color=INK2)
plt.savefig("/mnt/project-files/katip-lab-legal/baseline_vs_ours.png",dpi=200,bbox_inches="tight",facecolor="white")
