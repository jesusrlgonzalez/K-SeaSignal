from pathlib import Path
import json
from i28.ml_experiment import features,run_experiment
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'DATOS_FUENTES/04_SINTETICOS'

def test_features_reject_naive():
 assert features({'BaseDateTime':'2024-08-01 00:00:00'}) is None

def test_features_include_sentinel_flags():
 f=features({'BaseDateTime':'2024-08-01T00:00:00Z','SOG':'102.3','COG':'360'})
 assert f[-2:]==[1.,1.]

def test_ml_separated_by_vessels_and_time(tmp_path):
 x=run_experiment(DATA/'ais_dirty_SYNTHETIC.csv',DATA/'vessel_reference_SYNTHETIC.csv',DATA/'injection_truth_DO_NOT_TRAIN.csv',tmp_path/'x.json')
 assert x['train_vessels']==12 and x['test_vessels']==4
 assert x['train_rows']>100 and x['holdout_rows']>100
 assert x['kind']=='EXPLORATORY_SYNTHETIC_ISOLATION_FOREST'

def test_ml_experiment_replay(tmp_path):
 args=[DATA/'ais_dirty_SYNTHETIC.csv',DATA/'vessel_reference_SYNTHETIC.csv',DATA/'injection_truth_DO_NOT_TRAIN.csv']
 run_experiment(*args,tmp_path/'one.json')
 run_experiment(*args,tmp_path/'two.json')
 assert (tmp_path/'one.json').read_bytes()==(tmp_path/'two.json').read_bytes()
