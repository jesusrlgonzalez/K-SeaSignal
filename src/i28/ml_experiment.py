"""Exploratory, unsupervised, group+time held-out quality anomaly baseline.
SYNTHETIC ONLY, not misconduct detection. Evaluation labels never enter fit() or score().
"""
import csv,json,math
from pathlib import Path
from collections import Counter
from sklearn.ensemble import IsolationForest
import numpy as np
from .core import safe_float,parse_utc,decide_one,load_reference

LABEL_EXCLUDE={'UNKNOWN_SPEED_SENTINEL','UNKNOWN_COURSE_SENTINEL','RECEIVER_DUPLICATE'}

def features(row):
    """Use available single-message technical features ONLY; no target or future messages."""
    sog=safe_float(row.get('SOG'));cog=safe_float(row.get('COG'))
    dt=parse_utc(row.get('BaseDateTime'));observed=parse_utc(row.get('ObservedTimestamp'))
    if dt is None:return None
    lag=(observed-dt).total_seconds()/60 if observed else 0.
    # no GPS coordinates; quality-agnostic early ML baseline lacks trajectory context
    return [float(sog) if sog is not None else 0.,float(cog) if cog is not None else 0.,
            max(-600,min(600,lag)), 1. if sog is None or abs(sog-102.3)<1e-5 else 0.,
            1. if cog is None or abs(cog-360)<1e-5 else 0.]

def run_experiment(source,reference,truth,out):
    rows=list(csv.DictReader(open(source,newline='',encoding='utf8')))
    catalog=load_reference(reference)
    keys=sorted(catalog)
    train=set(keys[:12]);test=set(keys[12:])
    anchor=parse_utc('2024-08-01T12:00:00Z')
    train_features=[];test_features=[];test_ids=[]
    for r in rows:
        f=features(r);when=parse_utc(r.get('BaseDateTime'))
        if f is None or when is None:continue
        m=r['MMSI'];decision=decide_one(r,catalog)
        if m in train and when<anchor and decision['status']=='CANDIDATE':train_features.append(f)
        if m in test and when>=anchor:
            test_features.append(f);test_ids.append(r['row_id'])
    if len(train_features)<100 or len(test_features)<100:raise ValueError('insufficient group-time split')
    model=IsolationForest(n_estimators=100,contamination=0.06,random_state=2801,n_jobs=1)
    model.fit(np.array(train_features))
    scores=-model.score_samples(np.array(test_features))
    # rank fixed reviewer budget 10% of available examples, chosen BEFORE seeing truth
    k=max(1,round(len(test_ids)*.10))
    order=np.argsort(-scores,kind='stable')[:k]
    selected={test_ids[i] for i in order}
    # Evaluator only from here, not used in fit or rank selection
    positives={r['row_id'] for r in csv.DictReader(open(truth,newline='',encoding='utf8')) if r['injected_type'] not in LABEL_EXCLUDE}
    positive_test=positives.intersection(test_ids)
    tp=len(selected.intersection(positive_test))
    result={'kind':'EXPLORATORY_SYNTHETIC_ISOLATION_FOREST','train_vessels':len(train), 'test_vessels':len(test),
            'train_rows':len(train_features),'holdout_rows':len(test_features),
            'training_time':'2024-08-01 00:00..11:59Z','holdout_time':'2024-08-01 >=12:00Z',
            'precision_at_10pct_review_budget':round(tp/k,4),
            'recall_at_10pct_review_budget':round(tp/len(positive_test),4) if positive_test else None,
            'review_budget':k,'known_injected_holdout':len(positive_test),'found_injected_holdout':tp,
            'limitation':'Synthetic injection labels are not independent operational ground truth; quality only, no criminal or vessel misconduct detection.'}
    Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf8')
    return result
