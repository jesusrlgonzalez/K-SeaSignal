"""Conservative, OFFLINE, NOAA MarineCadastre AIS CSV translator.
Does not invent receipt timestamps, trusted catalogs or fixed vessel identities.
"""
import csv
from pathlib import Path
from .core import FIELDS

def adapt(input_csv,output_csv):
    inp=Path(input_csv);out=Path(output_csv)
    if out.resolve()==inp.resolve():raise ValueError('source must remain immutable')
    out.parent.mkdir(parents=True,exist_ok=True)
    with inp.open(newline='',encoding='utf-8-sig') as f, out.open('w',newline='',encoding='utf8') as g:
        reader=csv.DictReader(f)
        required={'MMSI','BaseDateTime','LAT','LON','SOG','COG'}
        if not reader.fieldnames or not required<=set(reader.fieldnames):raise ValueError('NOAA schema incompatible; manual review required')
        w=csv.DictWriter(g,fieldnames=FIELDS);w.writeheader()
        for index,r in enumerate(reader):
            target={k:'' for k in FIELDS}
            target.update({'row_id':f'NOAA_{index:09d}','MMSI':r['MMSI'],'BaseDateTime':r['BaseDateTime'],
                           'LAT':r['LAT'],'LON':r['LON'],'SOG':r['SOG'],'COG':r['COG'],
                           'Heading':r.get('Heading',''),'Status':r.get('Status',''),
                           'TransceiverClass':r.get('TransceiverClass',''),
                           'ObservedTimestamp':'', 'source':'NOAA_EXTERNAL_PENDING_ADMISSION'})
            w.writerow(target)
    return out
