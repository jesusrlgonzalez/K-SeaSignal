"""No network access and no externally effective action."""
import argparse,json
from .core import run

def main():
 p=argparse.ArgumentParser(description='I28 AIS synthetic/data-quality auditor')
 p.add_argument('command',choices=['audit'])
 p.add_argument('--source',required=True);p.add_argument('--reference',required=True);p.add_argument('--out',required=True)
 p.add_argument('--as-of',default='2024-08-30T00:00:00Z')
 a=p.parse_args();print(json.dumps(run(a.source,a.reference,a.out,a.as_of),indent=2,sort_keys=True))
if __name__=='__main__':main()
