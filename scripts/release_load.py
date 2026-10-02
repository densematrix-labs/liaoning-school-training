"""Read-only synthetic-instance load check; never seeds or changes a database."""
import asyncio,json,os,time
from pathlib import Path
import httpx
from app.services.auth import AuthService
async def main():
    assert os.getenv('RELEASE_SMOKE_ALLOWED')=='true'
    duration=int(os.getenv('SMOKE_LOAD_SECONDS','60'));end=time.monotonic()+duration;times=[];failures=[]
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=30) as client:
        async def visitor(i):
            token=AuthService.create_access_token({'sub':f'perf-user-{i}','role':'student'})
            while time.monotonic()<end:
                start=time.monotonic()
                try:
                    result=await client.get('/api/v1/scores/',headers={'Authorization':'Bearer '+token});result.raise_for_status();assert result.json()['total']>0
                    times.append(time.monotonic()-start)
                except Exception as exc:failures.append(type(exc).__name__)
                await asyncio.sleep(max(0,.5-(time.monotonic()-start)))
        await asyncio.gather(*(visitor(i) for i in range(50)))
    times.sort();result={'users':50,'duration_seconds':duration,'requests':len(times),'errors':len(failures),'p95_seconds':round(times[min(len(times)-1,int(len(times)*.95))],3),'max_seconds':round(max(times),3),'host':'Docker Desktop emulated linux/amd64; not school acceptance'}
    Path('/data/release-load-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
asyncio.run(main())
