"""Measure complete plugin CPU cost in an isolated RAM workspace; no game benchmark.
The raw RDR2 thumbnail seeds capture only when Gamescope has no new static frame.
"""
import asyncio,importlib.util,sys,types,logging,json,shutil,hashlib,statistics
from pathlib import Path
stage=Path(sys.argv[1]);home=Path.home()/'AsusNPU'
sys.modules['decky']=types.SimpleNamespace(DECKY_USER_HOME=str(Path.home()),logger=logging.getLogger('color-test'))
s=importlib.util.spec_from_file_location('color_lab_main',stage/'main.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
async def test():
 p=m.Plugin();rows=[]
 try:
  await p._main();p.task.cancel();await asyncio.gather(p.task,return_exceptions=True)
  p.work_root=Path('/run/user/1000/color-lab-total-bench');p.work_root.mkdir(exist_ok=True);p.settings_file=p.work_root/'settings.json'
  token=p.active_display['key']+p.active_app['key'];cache=p.work_root/('frame-'+hashlib.sha256(token.encode()).hexdigest()[:16]+'.rgb');shutil.copy(home/'pw-valid.rgb',cache)
  for model,engine in [('adaptive','cpu'),('adaptive','npu'),('hdr','cpu'),('hdr','npu')]:
   await p.configure({'auto':False,'enabled':True,'model_id':model,'engine':engine})
   for i in range(int(sys.argv[2]) if len(sys.argv)>2 else 3):
    r=await p.analyze(True);assert not r['last_error'] and not r['waiting'],r
    row={k:r[k] for k in ['model_id','engine','analysis_ms','analysis_cpu_ms','capture_ms','cycle_ms','cycle_cpu_ms']};row['iteration']=i;rows.append(row)
    if len(sys.argv)<4:print(json.dumps(row),flush=True)
  (home/'hdr-probe/full-cycle-benchmark.json').write_text(json.dumps(rows,indent=2))
  summary={}
  for model,engine in [('adaptive','cpu'),('adaptive','npu'),('hdr','cpu'),('hdr','npu')]:
   group=[r for r in rows if r['model_id']==model and r['engine']==engine and r['iteration']>0]
   summary[model+'-'+engine]={key:statistics.median(r[key] for r in group) for key in ['analysis_ms','analysis_cpu_ms','cycle_ms','cycle_cpu_ms']}
  (home/'hdr-probe/full-cycle-benchmark-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
 finally:await p._unload()
asyncio.run(test())
