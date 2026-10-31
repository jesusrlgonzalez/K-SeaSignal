"""Deterministic AIS-quality engine. No writes to external systems; no abuse accusations."""
import csv, math, json, re, hashlib, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict

KNOT_KM_H=1.852
CRITICAL={'INVALID_MMSI','INVALID_TIME','INVALID_LAT','INVALID_LON','NEGATIVE_SOG'}
FIELDS=['row_id','MMSI','BaseDateTime','LAT','LON','SOG','COG','Heading','Status','TransceiverClass','ObservedTimestamp','source']

def parse_utc(text):
    if not text or not isinstance(text,str):return None
    try:
        t=datetime.fromisoformat(text.strip().replace('Z','+00:00'))
        if t.tzinfo is None:return None  # no implicit timezone
        return t.astimezone(timezone.utc)
    except (ValueError,OverflowError,TypeError):return None

def safe_float(x):
    try:
        if x is None or str(x).strip()=='':return None
        n=float(x)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def latlon_ok(lat,lon):return lat is not None and lon is not None and -90<=lat<=90 and -180<=lon<=180

def haversine_km(lat1,lon1,lat2,lon2):
    """Correctly handles cross-antimeridian longitude wrap through sin(dlon/2)."""
    vals=[lat1,lon1,lat2,lon2]
    if not all(v is not None and math.isfinite(v) for v in vals):raise ValueError('coordinates nonfinite')
    if not latlon_ok(lat1,lon1) or not latlon_ok(lat2,lon2):raise ValueError('coordinate range')
    p1,p2=math.radians(lat1),math.radians(lat2)
    dl=math.radians(((lon2-lon1+180)%360)-180)
    dp=p2-p1
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(max(0,a))))

def safe_csv_value(s):
    """Escape strings before spreadsheet export; preserve original unmodified."""
    s='' if s is None else str(s)
    return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r')) else s

def load_reference(path):
    with open(path,newline='',encoding='utf-8-sig') as f:
        r=list(csv.DictReader(f))
    out={}
    for x in r:
        m=x.get('MMSI','')
        if m in out:raise ValueError('duplicate reference MMSI')
        if not re.fullmatch(r'\d{9}',m):raise ValueError('bad catalog MMSI')
        out[m]=x
    if not out:raise ValueError('empty reference')
    return out

def decide_one(record, reference,as_of=None,synthetic_mode=True):
    flags=[]; notes=[]
    rid=record.get('row_id','');m=record.get('MMSI','')
    if not re.fullmatch(r'\d{9}',m):flags.append('INVALID_MMSI')
    elif m not in reference:flags.append('UNKNOWN_MMSI')
    ts=parse_utc(record.get('BaseDateTime'))
    if ts is None:flags.append('INVALID_TIME')
    elif as_of is not None and ts>as_of:flags.append('FUTURE_EVENT')
    obs=parse_utc(record.get('ObservedTimestamp'))
    if not record.get('ObservedTimestamp'):notes.append('RECEIPT_NOT_PROVIDED')
    elif obs is None:flags.append('INVALID_OBSERVED_TIME')
    elif ts is not None:
        delta=(obs-ts).total_seconds()
        if delta < -60:flags.append('OBSERVED_BEFORE_EVENT')
        elif delta > 3600:flags.append('LATE_RECEIPT')
    lat=safe_float(record.get('LAT'));lon=safe_float(record.get('LON'))
    if lat is None or not (-90<=lat<=90):flags.append('INVALID_LAT')
    if lon is None or not (-180<=lon<=180):flags.append('INVALID_LON')
    sog=safe_float(record.get('SOG'))
    if sog is None:notes.append('SOG_NOT_AVAILABLE')
    elif abs(sog-102.3)<1e-9:notes.append('SOG_SENTINEL_NOT_AVAILABLE');sog=None
    elif sog<0:flags.append('NEGATIVE_SOG')
    elif sog>55:flags.append('HIGH_REPORTED_SOG')
    cog=safe_float(record.get('COG'))
    if cog is None or abs(cog-360.0)<1e-9:notes.append('COG_NOT_AVAILABLE');cog=None
    elif not 0<=cog<360:flags.append('INVALID_COG')
    heading=safe_float(record.get('Heading'))
    if heading is None or abs(heading-511)<1e-9:notes.append('HEADING_NOT_AVAILABLE')
    elif not (0<=heading<=359):flags.append('INVALID_HEADING')
    if not record.get('Status'):notes.append('NAV_STATUS_NOT_PROVIDED')
    src=record.get('source','')
    if src and src.lstrip().startswith(('=','+','-','@')):flags.append('SPREADSHEET_FORMULA_RISK')
    status=('QUARANTINE' if set(flags)&CRITICAL else 'REVIEW' if flags else 'CANDIDATE')
    return {'row_id':rid,'MMSI':m,'timestamp':ts.isoformat() if ts else '', 'lat':lat,'lon':lon,
            'sog_kn':sog,'cog':cog,'status':status,'flags':sorted(set(flags)), 'notes':sorted(set(notes))}

def audit_rows(records,reference,as_of=None):
    """Every input row produces exactly one decision. No positional origin tracking or attribution."""
    seen_ids=set();out=[];by_key=defaultdict(list)
    for n,row in enumerate(records):
        if not row.get('row_id') or row['row_id'] in seen_ids:raise ValueError('row_id required and unique')
        seen_ids.add(row['row_id'])
        d=decide_one(row,reference,as_of=as_of);d['input_index']=n
        out.append(d)
        if d['timestamp'] and d['MMSI'] and d['lat'] is not None and d['lon'] is not None:
            by_key[(d['MMSI'],d['timestamp'])].append(d)
    # Repeated broadcast / conflicting positions: preserve every row.
    for candidates in by_key.values():
        if len(candidates)>1:
            distinct={(d['lat'],d['lon']) for d in candidates}
            for d in candidates:
                if len(distinct)>1: d['flags'].append('CONFLICTING_SAME_TIMESTAMP')
                else:d['notes'].append('REPEATED_BROADCAST')
                if d['status']=='CANDIDATE':d['status']='REVIEW'
    # Compare only consecutive candidate fixes, chronological per MMSI.
    vessels=defaultdict(list)
    for d in out:
        if d['status']=='CANDIDATE':vessels[d['MMSI']].append(d)
    signals=[]
    for m,fixes in sorted(vessels.items()):
        fixes.sort(key=lambda d:(d['timestamp'],d['row_id']))
        prev=None
        for d in fixes:
            if prev is not None:
                secs=(datetime.fromisoformat(d['timestamp'])-datetime.fromisoformat(prev['timestamp'])).total_seconds()
                if secs>45*60: signals.append({'row_id':d['row_id'],'MMSI':m,'type':'OBSERVATION_GAP','value':round(secs/60,2),'unit':'minutes','decision':'DATA_COVERAGE_ONLY'})
                elif secs>0:
                    dist=haversine_km(prev['lat'],prev['lon'],d['lat'],d['lon'])
                    kn=dist/(secs/3600)/KNOT_KM_H
                    if kn>45:
                        signals.append({'row_id':d['row_id'],'MMSI':m,'type':'IMPOSSIBLE_OR_UNLIKELY_JUMP','value':round(kn,3),'unit':'knots','decision':'TRIAGE_NOT_MISCONDUCT'})
                        d['flags'].append('TRAJECTORY_SPEED_JUMP')
                        d['status']='REVIEW'
                        # do not advance previous accepted point on a suspect fix
                        continue
            prev=d
    return out,signals

def export_synthetic_geojson(decisions,path):
    """Offline fixture-only track preview; split on gaps and antimeridian."""
    from collections import defaultdict
    dct=defaultdict(list)
    for d in decisions:
        if d['status']=='CANDIDATE' and d['timestamp'] and d['lat'] is not None and d['lon'] is not None:
            dct[d['MMSI']].append(d)
    features=[]
    for m,fixes in sorted(dct.items()):
        fixes.sort(key=lambda x:(x['timestamp'],x['row_id']))
        segments=[];seq=[];prior=None
        for d in fixes:
            if prior:
                dt_sec=(datetime.fromisoformat(d['timestamp'])-datetime.fromisoformat(prior['timestamp'])).total_seconds()
                if dt_sec>45*60 or abs(d['lon']-prior['lon'])>180:
                    if len(seq)>1:segments.append(seq)
                    seq=[]
            seq.append([d['lon'],d['lat']]);prior=d
        if len(seq)>1:segments.append(seq)
        if segments:
            features.append({'type':'Feature','properties':{'synthetic_vessel':m,'not_for_navigation':True},
                             'geometry':{'type':'MultiLineString','coordinates':segments}})
    payload={'type':'FeatureCollection','features':features,'metadata':{'data_class':'SYNTHETIC_ONLY','not_for_navigation':True}}
    Path(path).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf8')
    return len(features)

def run(source,reference,out,as_of=None):
    source=Path(source);reference=Path(reference);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    records=list(csv.DictReader(source.open(newline='',encoding='utf-8-sig')))
    catalog=load_reference(reference)
    decisions,signals=audit_rows(records,catalog,parse_utc(as_of) if as_of else None)
    counts=Counter(d['status'] for d in decisions)
    assert len(records)==len(decisions)==sum(counts.values())
    report={'project':'I28','data_class':'SYNTHETIC' if 'SINTETICOS' in str(source) else 'EXTERNAL_NEEDS_ADMISSION',
            'rows':len(records),'candidate':counts['CANDIDATE'],'review':counts['REVIEW'],'quarantine':counts['QUARANTINE'],
            'signals':len(signals),'signals_are_not_crime_evidence':True,'read_only':True,
            'raw_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
            'as_of':as_of or 'NONE',
            'decisions_flags':dict(sorted(Counter(flag for d in decisions for flag in set(d['flags'])).items())),
            'signal_types':dict(sorted(Counter(s['type'] for s in signals).items()))}
    (out/'quality_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf8')
    for status,path in [('CANDIDATE','candidates.csv'),('REVIEW','review.csv'),('QUARANTINE','quarantine.csv')]:
        with (out/path).open('w',newline='',encoding='utf8') as f:
            w=csv.writer(f);w.writerow(['row_id','MMSI','timestamp','lat','lon','flags','notes'])
            for d in decisions:
                if d['status']==status:
                    w.writerow([safe_csv_value(d['row_id']),safe_csv_value(d['MMSI']),d['timestamp'],d['lat'],d['lon'],'|'.join(d['flags']),'|'.join(d['notes'])])
    with (out/'trajectory_signals.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=['row_id','MMSI','type','value','unit','decision']);w.writeheader();w.writerows(signals)
    db=out/'quality_readonly_api.sqlite'
    if db.exists():db.unlink()
    cx=sqlite3.connect(db)
    cx.execute('create table ais_decisions(row_id text primary key, mmsi text, status text, flag_count integer, event_time text)')
    cx.executemany('insert into ais_decisions values(?,?,?,?,?)',[(d['row_id'],d['MMSI'],d['status'],len(d['flags']),d['timestamp']) for d in decisions]);cx.commit();cx.close()
    if report['data_class']=='SYNTHETIC':
        export_synthetic_geojson(decisions,out/'synthetic_tracks_NOT_FOR_NAVIGATION.geojson')
    return report
