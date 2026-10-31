import csv,json,sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from i28.core import run
from i28.api import create_app
from i28.adapter_noaa import adapt
from i28.experiment import evaluate
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'DATOS_FUENTES/04_SINTETICOS/ais_dirty_SYNTHETIC.csv'
REF=ROOT/'DATOS_FUENTES/04_SINTETICOS/vessel_reference_SYNTHETIC.csv'
TRUTH=ROOT/'DATOS_FUENTES/04_SINTETICOS/injection_truth_DO_NOT_TRAIN.csv'

def test_run_reconciles(tmp_path):
 r=run(SOURCE,REF,tmp_path/'a','2024-08-30T00:00:00Z')
 assert r['rows']==r['candidate']+r['review']+r['quarantine']
 assert r['raw_sha256']==__import__('hashlib').sha256(SOURCE.read_bytes()).hexdigest()

def test_original_immutable(tmp_path):
 before=SOURCE.read_bytes();run(SOURCE,REF,tmp_path/'b');assert SOURCE.read_bytes()==before

def test_api_aggregates_no_positions(tmp_path):
 run(SOURCE,REF,tmp_path/'c');client=TestClient(create_app(tmp_path/'c/quality_readonly_api.sqlite'))
 resp=client.get('/summary');assert resp.status_code==200
 assert 'lat' not in str(resp.json()).lower()
 assert client.get('/health').json()['no_live_tracking'] is True

def test_api_reject_bad_id(tmp_path):
 run(SOURCE,REF,tmp_path/'d');client=TestClient(create_app(tmp_path/'d/quality_readonly_api.sqlite'))
 assert client.get('/vessel/123/quality').status_code==400

def test_api_missing_record_returns_404(tmp_path):
 run(SOURCE,REF,tmp_path/'e');client=TestClient(create_app(tmp_path/'e/quality_readonly_api.sqlite'))
 assert client.get('/vessel/111111111/quality').status_code==404

def test_db_read_only(tmp_path):
 run(SOURCE,REF,tmp_path/'f');db=sqlite3.connect(f'file:{tmp_path}/f/quality_readonly_api.sqlite?mode=ro',uri=True)
 with pytest.raises(sqlite3.OperationalError):db.execute("delete from ais_decisions")
 db.close()

def test_real_adapter_does_not_invent_receipt(tmp_path):
 p=tmp_path/'noaa.csv';p.write_text('MMSI,BaseDateTime,LAT,LON,SOG,COG\n366900001,2024-08-01T00:00:00Z,20,-80,4,90\n')
 q=tmp_path/'normal.csv';adapt(p,q)
 with q.open() as f:row=next(csv.DictReader(f))
 assert row['ObservedTimestamp']=='' and row['source']=='NOAA_EXTERNAL_PENDING_ADMISSION'

def test_adapter_fail_closed_wrong_schema(tmp_path):
 p=tmp_path/'broken.csv';p.write_text('MMSI,BaseDateTime,LAT\n1,2024-01-01,20\n')
 with pytest.raises(ValueError):adapt(p,tmp_path/'out.csv')

def test_adapter_preserves_input(tmp_path):
 p=tmp_path/'noaa.csv';p.write_text('MMSI,BaseDateTime,LAT,LON,SOG,COG\n366900001,2024-08-01T00:00:00Z,20,-80,4,90\n');before=p.read_bytes();adapt(p,tmp_path/'q.csv');assert p.read_bytes()==before

def test_adapter_same_path_forbidden(tmp_path):
 p=tmp_path/'x.csv';p.write_text('a\n');
 with pytest.raises(ValueError):adapt(p,p)

def test_synthetic_evaluation_is_separate(tmp_path):
 run(SOURCE,REF,tmp_path/'f');res=evaluate(SOURCE,tmp_path/'f',TRUTH,tmp_path/'eval.json')
 assert res['evaluation_set']=='SYNTHETIC_INJECTED_ONLY' and 0<=res['injected_recall']<=1

def test_schema_output_files(tmp_path):
 run(SOURCE,REF,tmp_path/'g');assert len(list((tmp_path/'g').iterdir()))==7

def test_replay_identical(tmp_path):
 run(SOURCE,REF,tmp_path/'h');run(SOURCE,REF,tmp_path/'i')
 import hashlib
 a=sorted(p for p in (tmp_path/'h').iterdir() if p.is_file())
 b=sorted(p for p in (tmp_path/'i').iterdir() if p.is_file())
 assert [p.name for p in a]==[p.name for p in b]
 assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in a]==[hashlib.sha256(p.read_bytes()).hexdigest() for p in b]

def test_no_manifest_truth_in_audit(tmp_path):
 run(SOURCE,REF,tmp_path/'j')
 report=json.loads((tmp_path/'j/quality_report.json').read_text())
 assert not any('truth' in k for k in report)


def test_synthetic_geospatial_preview_not_live(tmp_path):
    run(SOURCE,REF,tmp_path/'preview')
    f=tmp_path/'preview/synthetic_tracks_NOT_FOR_NAVIGATION.geojson'
    d=json.loads(f.read_text())
    assert d['metadata']['data_class']=='SYNTHETIC_ONLY'
    assert d['features']
    for feat in d['features']:
        for line in feat['geometry']['coordinates']:
            assert all(abs(line[i][0]-line[i-1][0])<=180 for i in range(1,len(line)))

def test_external_data_does_not_export_tracks(tmp_path):
    source=tmp_path/'real_mock.csv'
    source.write_bytes(SOURCE.read_bytes())
    run(source,REF,tmp_path/'external')
    assert not (tmp_path/'external/synthetic_tracks_NOT_FOR_NAVIGATION.geojson').exists()
