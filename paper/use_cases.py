# Builds paper/use_cases.json and paper/use_cases.csv: the recommended setup per use case, with every number
# read from the saved KVKK-Bench results (run from the repo root on legal-study). Table 3 of the paper prints this.
import json, csv
R='lab/legal/bench/results/'
def J(p): return json.load(open(R+p))
def pct(x): return float(f"{100*x+1e-9:.1f}")
def trk(s,t,k):
    v=J(f'{s}.json')['tracks'][t][k]; return round(v,1) if k=='false_per_1k_words' else pct(v)
def fmt(s,f): return pct(J(f'format/{s}.json')['formats'][f]['leak_rate'])
def photo(s):
    p=J(f'photo/{s}.json'); return pct(p['leak_rate']), pct(p['streets_over_masked']/p['streets'])
def pps(s): return round(1000/J(f'{s}.json')['ms_per_page'],1)
BROWSER_S_PER_PAGE={'berturk-v2':3.8,'mini-v2':1.0,'tiny-f':0.03}  # one Chrome tab, 500-word page (Section 6)
rows=[
 dict(use_case='Send a court document to an AI assistant from a computer', setup='Katip Kalkan connector with Katip Mask Base',
      system='berturk-v2', reader='UDF/Word/PDF text; PaddleOCR for scans', runs='laptop, offline',
      leak_pct={'court text, Turkish names':trk('berturk-v2','court-turkish','leak_rate'),'court text, foreign names':trk('berturk-v2','court-foreign','leak_rate'),
                'forms, all value types':pct(J('forms/berturk-v2.json')['leak_rate'])},
      false_alarms_per_1k_words=trk('berturk-v2','court-turkish','false_per_1k_words'), speed=f"{pps('berturk-v2')} pages/s",
      caveat='Kalkan ships Nano by default; choose Base for lower leak.'),
 dict(use_case='Mask in a browser, nothing installed', setup='Katip Mask Mini (web page default)',
      system='mini-v2', reader='browser text layer; OCR in the page', runs='browser tab',
      leak_pct={'court text, Turkish names':trk('mini-v2','court-turkish','leak_rate'),'court text, foreign names':trk('mini-v2','court-foreign','leak_rate'),
                'forms, all value types':pct(J('forms/mini-v2.json')['leak_rate'])},
      false_alarms_per_1k_words=trk('mini-v2','court-turkish','false_per_1k_words'), speed=f"{BROWSER_S_PER_PAGE['mini-v2']} s/page in browser",
      caveat='Everyday text leaks '+str(trk('mini-v2','prose','leak_rate'))+'%; review before sending.'),
 dict(use_case='Many court pages fast, or a weak device', setup='Katip Mask Nano (fast mode)',
      system='tiny-f', reader='as above', runs='browser tab or laptop',
      leak_pct={'court text, Turkish names':trk('tiny-f','court-turkish','leak_rate'),'court text, foreign names':trk('tiny-f','court-foreign','leak_rate'),
                'forms, all value types':pct(J('forms/tiny-f.json')['leak_rate'])},
      false_alarms_per_1k_words=trk('tiny-f','court-turkish','false_per_1k_words'), speed=f"{pps('tiny-f')} pages/s; {BROWSER_S_PER_PAGE['tiny-f']} s/page in browser",
      caveat='Not for everyday text: leaks '+str(trk('tiny-f','prose','leak_rate'))+'%.'),
 dict(use_case='Scanned PDFs', setup='Katip Mask Base + PaddleOCR PP-OCRv5',
      system='berturk-v2', reader='PaddleOCR (200 dpi)', runs='laptop, offline',
      leak_pct={'scanned forms':fmt('berturk-v2','scan'),'same forms, digital PDF':fmt('berturk-v2','pdf')},
      false_alarms_per_1k_words=None, speed=f"{pps('berturk-v2')} pages/s plus OCR", caveat='Synthetic forms only; not ranked.'),
 dict(use_case='UYAP UDF and Word files', setup='Katip Mask Base',
      system='berturk-v2', reader='UDF content.xml / Word paragraphs', runs='laptop or browser',
      leak_pct={'UDF':fmt('berturk-v2','udf'),'Word':fmt('berturk-v2','docx')},
      false_alarms_per_1k_words=None, speed=f"{pps('berturk-v2')} pages/s", caveat='Synthetic forms only; not ranked.'),
 dict(use_case='Phone photos of hand-filled forms', setup='Katip Mask Base + Katip OCR with ink masks',
      system='berturk-v2', reader='PaddleOCR on handwriting, Tesseract otherwise', runs='laptop or browser',
      leak_pct={'values on photos':photo('berturk-v2')[0]}, over_masked_street_names_pct=photo('berturk-v2')[1],
      false_alarms_per_1k_words=None, speed='n/a', caveat='Leaks are addresses; low-leak rivals over-mask (ModernBERT-TR PII: '+str(photo('cosmos-pii')[1])+'%).'),
 dict(use_case='Everyday text (letters, e-mails), lowest leak', setup='XLM-R Large (CoNLL), server only; otherwise Base plus review',
      system='xlmr-conll', reader='plain text', runs='workstation (2.2 GB), not browser',
      leak_pct={'everyday text, XLM-R Large':trk('xlmr-conll','prose','leak_rate'),'everyday text, Katip Base':trk('berturk-v2','prose','leak_rate')},
      false_alarms_per_1k_words=trk('xlmr-conll','prose','false_per_1k_words'), speed=f"{pps('xlmr-conll')} pages/s",
      caveat='Names only: misses IDs and IBANs (forms F2 '+str(pct(J('forms/xlmr-conll.json')['F2 all tracks']))+'). No setup is safe here without review.'),
]
json.dump({'benchmark':'KVKK-Bench v0.1.2','note':'leak = % of personal-data characters left readable; synthetic tracks are not ranked','use_cases':rows},
          open('paper/use_cases.json','w'),ensure_ascii=False,indent=1)
with open('paper/use_cases.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['use_case','setup','system','reader','runs','leak_pct','over_masked_street_names_pct','false_alarms_per_1k_words','speed','caveat'])
    for r in rows: w.writerow([r['use_case'],r['setup'],r['system'],r['reader'],r['runs'],'; '.join(f'{k}: {v}' for k,v in r['leak_pct'].items()),
                               r.get('over_masked_street_names_pct',''),r['false_alarms_per_1k_words'] if r['false_alarms_per_1k_words'] is not None else '',r['speed'],r['caveat']])
for r in rows: print(r['use_case'],'|',r['leak_pct'],r.get('over_masked_street_names_pct'),r['false_alarms_per_1k_words'],r['speed'],'|',r['caveat'])
