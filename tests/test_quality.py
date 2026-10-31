import pytest
from i28.core import parse_utc,safe_float,latlon_ok,haversine_km,safe_csv_value,decide_one,audit_rows,load_reference
REF={'366900001':{'MMSI':'366900001'}}

def obs(**kw):
 x={'row_id':'x','MMSI':'366900001','BaseDateTime':'2024-08-01T00:00:00Z','LAT':'20','LON':'-90',
    'SOG':'5','COG':'90','Heading':'91','Status':'0','TransceiverClass':'A','ObservedTimestamp':'2024-08-01T00:00:10Z','source':'SYNTHETIC_AIS'}
 x.update(kw);return x

@pytest.mark.parametrize('text',[None,'','oops','2024-13-40T01:00:00Z','2024-08-01T02:00:00'])
def test_bad_time(text):assert parse_utc(text) is None
@pytest.mark.parametrize('text',[None,'','nan','inf','-inf','twenty'])
def test_bad_float(text):assert safe_float(text) is None
@pytest.mark.parametrize('lat,lon',[(-91,0),(91,0),(0,181),(0,-181),(None,1),(1,None)])
def test_bounds(lat,lon):assert not latlon_ok(lat,lon)

def test_valid_utc():assert parse_utc('2024-08-01T00:00:00Z').year==2024

def test_antimeridian_short_distance():assert haversine_km(10,179.9,10,-179.9)<24

def test_same_location_zero():assert haversine_km(20,80,20,80)==0

def test_bad_coord_raises():
 with pytest.raises(ValueError):haversine_km(92,0,20,0)
@pytest.mark.parametrize('k,v', [('MMSI','abc'),('BaseDateTime','bad'),('LAT','95'),('LON','181'),('SOG','-5')])
def test_quarantine(k,v):assert decide_one(obs(**{k:v}),REF)['status']=='QUARANTINE'
@pytest.mark.parametrize('k,v,code',[('MMSI','399888777','UNKNOWN_MMSI'),('COG','491','INVALID_COG'),('SOG','150','HIGH_REPORTED_SOG'),('ObservedTimestamp','2024-08-01T04:00:00Z','LATE_RECEIPT'),('source','=HYPERLINK("x")','SPREADSHEET_FORMULA_RISK')])
def test_review(k,v,code):
 d=decide_one(obs(**{k:v}),REF);assert d['status']=='REVIEW' and code in d['flags']

def test_missing_sog_valid_sentinel():
 d=decide_one(obs(SOG='102.3'),REF);assert d['status']=='CANDIDATE' and 'SOG_SENTINEL_NOT_AVAILABLE' in d['notes']

def test_missing_cog_valid_sentinel():
 d=decide_one(obs(COG='360'),REF);assert d['status']=='CANDIDATE' and 'COG_NOT_AVAILABLE' in d['notes']

def test_heading_sentinel_valid():assert decide_one(obs(Heading='511'),REF)['status']=='CANDIDATE'

def test_missing_receipt_not_fabricated():
 d=decide_one(obs(ObservedTimestamp=''),REF);assert d['status']=='CANDIDATE' and 'RECEIPT_NOT_PROVIDED' in d['notes']

def test_observed_before_event():assert 'OBSERVED_BEFORE_EVENT' in decide_one(obs(ObservedTimestamp='2024-07-31T22:00:00Z'),REF)['flags']

def test_as_of_future_review():
 t=parse_utc('2024-07-31T23:00:00Z');assert 'FUTURE_EVENT' in decide_one(obs(),REF,as_of=t)['flags']

def test_formula_escaped():assert safe_csv_value('=1+1').startswith("'=")

def test_plain_text_unchanged():assert safe_csv_value('normal')=='normal'

def test_duplicate_preservation():
 a=obs();b=obs(row_id='y');ds,_=audit_rows([a,b],REF)
 assert len(ds)==2 and all(d['status']=='REVIEW' for d in ds)
 assert all('REPEATED_BROADCAST' in d['notes'] for d in ds)

def test_conflicting_same_timestamp_review():
 a=obs();b=obs(row_id='y',LAT='30');ds,_=audit_rows([a,b],REF)
 assert all(d['status']=='REVIEW' for d in ds)
 assert all('CONFLICTING_SAME_TIMESTAMP' in d['flags'] for d in ds)

def test_duplicate_row_id_fails_closed():
 with pytest.raises(ValueError):audit_rows([obs(),obs()],REF)

def test_speed_jump_not_crime():
 a=obs();b=obs(row_id='b',LAT='30',BaseDateTime='2024-08-01T00:10:00Z',ObservedTimestamp='2024-08-01T00:10:10Z');ds,signals=audit_rows([a,b],REF)
 assert ds[1]['status']=='REVIEW'
 assert any(s['decision']=='TRIAGE_NOT_MISCONDUCT' for s in signals)

def test_long_gap_does_not_prove_switch_off():
 a=obs();b=obs(row_id='b',BaseDateTime='2024-08-01T04:00:00Z',ObservedTimestamp='2024-08-01T04:00:10Z');ds,signals=audit_rows([a,b],REF)
 assert ds[1]['status']=='CANDIDATE'
 assert any(s['type']=='OBSERVATION_GAP' for s in signals)

def test_baseline_candidate():assert decide_one(obs(),REF)['status']=='CANDIDATE'

def test_no_reference_duplicate(tmp_path):
 x=tmp_path/'r.csv';x.write_text('MMSI\n366900001\n366900001\n')
 with pytest.raises(ValueError):load_reference(x)
