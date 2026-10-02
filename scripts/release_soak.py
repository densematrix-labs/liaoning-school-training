"""Opt-in read-only health soak; record actual elapsed time, never simulate it.
Run in a disposable/approved container: python - --hours 24 < release_soak.py
"""
import argparse,json,time,urllib.request
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--hours',type=float,default=24);p.add_argument('--interval',type=float,default=30);args=p.parse_args()
start=time.monotonic();end=start+args.hours*3600;failures=0;count=0
while time.monotonic()<end:
    before=time.monotonic();count+=1
    try:
        with urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5) as r:assert json.load(r)['status']=='healthy'
        status='success'
    except Exception as e:failures+=1;status=type(e).__name__
    print(json.dumps({'time':datetime.now(timezone.utc).isoformat(),'status':status,'seconds':round(time.monotonic()-before,3)}),flush=True)
    time.sleep(min(args.interval,max(0,end-time.monotonic())))
print(json.dumps({'actual_elapsed_seconds':time.monotonic()-start,'checks':count,'failures':failures,'scope':'health-only; not a substitute for business workload acceptance'}),flush=True)
raise SystemExit(1 if failures else 0)
