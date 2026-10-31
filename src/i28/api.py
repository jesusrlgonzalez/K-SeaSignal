"""Read-only aggregate API; never publishes precise tracks or exposes raw payloads."""
from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException

def create_app(db_path):
    app=FastAPI(title='I28 Maritime Data Quality — Demo (no live tracking)')
    db_path=Path(db_path)
    def check():
        if not db_path.is_file():raise HTTPException(503,'local quality DB unavailable')
    @app.get('/health')
    def health():check();return {'status':'LOCAL_DEMO','no_live_tracking':True}
    @app.get('/summary')
    def summary():
        check()
        with sqlite3.connect(f'file:{db_path}?mode=ro',uri=True) as db:
            return {'data_class':'QUALITY_ONLY','counts':dict(db.execute('select status,count(*) from ais_decisions group by status').fetchall()),'no_misconduct_inferences':True}
    @app.get('/vessel/{mmsi}/quality')
    def vessel_quality(mmsi:str):
        check()
        if len(mmsi)!=9 or not mmsi.isdigit():raise HTTPException(400,'MMSI format')
        with sqlite3.connect(f'file:{db_path}?mode=ro',uri=True) as db:
            counts=dict(db.execute('select status,count(*) from ais_decisions where mmsi=? group by status',(mmsi,)).fetchall())
        if not counts:raise HTTPException(404,'no aggregate data')
        return {'MMSI':mmsi,'counts':counts,'coordinates_disclosed':False}
    return app
