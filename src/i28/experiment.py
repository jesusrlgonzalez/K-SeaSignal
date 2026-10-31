"""Exploratory ML only. Injection truth is evaluation-only, never passed to audit."""
import csv,json,math
from pathlib import Path
from collections import Counter

def evaluate(raw_csv,decisions_dir,truth_csv,out_path):
    """Synthetic injected event flag recall. This is NOT real-world recall."""
    truth={x['row_id'] for x in csv.DictReader(open(truth_csv,newline='',encoding='utf8')) if x['injected_type'] not in ('UNKNOWN_SPEED_SENTINEL','UNKNOWN_COURSE_SENTINEL','RECEIVER_DUPLICATE')}
    statuses={}
    for status,name in [('CANDIDATE','candidates.csv'),('REVIEW','review.csv'),('QUARANTINE','quarantine.csv')]:
        for x in csv.DictReader(open(Path(decisions_dir)/name,newline='',encoding='utf8')):statuses[x['row_id']]=status
    classified={rid for rid,st in statuses.items() if st!='CANDIDATE'}
    hit=len(truth&classified)
    metrics={'evaluation_set':'SYNTHETIC_INJECTED_ONLY','positives_excluding_valid_sentinels_and_repeated_broadcasts':len(truth),
             'injected_flagged':hit,'injected_recall':round(hit/len(truth),6) if truth else None,
             'all_flagged':len(classified),'precision_not_claimed':True,
             'caveat':'Designed rules and injection cases are dependent; never extrapolate to real AIS.'}
    Path(out_path).write_text(json.dumps(metrics,sort_keys=True,indent=2)+'\n',encoding='utf8')
    return metrics
