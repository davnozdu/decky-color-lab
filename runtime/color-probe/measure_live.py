"""Measure static Gamescope LUT application; NPU analysis is NOT running."""
import csv, json, os, statistics, subprocess, threading, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'runs'/time.strftime('live-look-%Y%m%d-%H%M%S');OUT.mkdir(parents=True)
GPU=Path('/sys/bus/pci/devices/0000:64:00.0');HW=next((GPU/'hwmon').glob('hwmon*'))
BAT=Path('/sys/class/power_supply/BAT0')
PPT=Path('/sys/class/firmware-attributes/asus-armoury/attributes/ppt_pl1_spl/current_value')
phase='transition';stop=threading.Event();manifest=[]
stream=os.environ.get('COLOR_STREAM')=='1'
def read(p):
    try:return int(p.read_text().strip())
    except (OSError,ValueError):return None
def cpu():
    x=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(x),x[3]+x[4]
def sample():
    old=cpu()
    with (OUT/'telemetry.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['time','phase','cpu_percent','gpu_busy','apu_w','battery_w','battery_status','tdp','gpu_mhz'])
        while not stop.is_set():
            c=cpu();t=c[0]-old[0];idle=c[1]-old[1];old=c
            power,bp,freq=[read(p) for p in [HW/'power1_average',BAT/'power_now',HW/'freq1_input']]
            w.writerow([time.monotonic(),phase,100*(t-idle)/t if t else 0,read(GPU/'gpu_busy_percent'),power/1e6 if power is not None else '',bp/1e6 if bp is not None else '',(BAT/'status').read_text().strip(),read(PPT),freq/1e6 if freq is not None else ''])
            f.flush();stop.wait(.5)
def look(enabled):
    command=['gamescopectl','set_look']
    command += [str(ROOT/'npu-look.cube') if enabled else '/dev/null']
    subprocess.run(command,check=True,timeout=10)
    (ROOT/'live-look-state.json').write_text(json.dumps({'enabled':enabled,'strength':.25,'time':time.time(),'lut':str(ROOT/'npu-look.cube')})+'\n')
thread=threading.Thread(target=sample,daemon=True);thread.start()
print('OUTPUT',OUT,flush=True)
try:
    for label,enabled,seconds in [('off1',False,25),('on1',True,40),('off2',False,25),('on2',True,40)]:
        if read(PPT)!=20:raise RuntimeError('Need fixed 20 W')
        look(enabled);time.sleep(4)
        phase=label;start=time.monotonic();print('PHASE',label,flush=True)
        with (OUT/(label+'.csv')).open('w') as f:
            subprocess.run([str(ROOT.parent/'npu-bridge'/('game-stats-stream' if stream else 'game-stats')),'1174180',str(seconds)],stdout=f,check=True,timeout=seconds+10)
        phase='transition';manifest.append({'label':label,'enabled':enabled,'start':start,'end':time.monotonic()})
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        if read(PPT)!=20:raise RuntimeError('TDP changed')
finally:
    stop.set();thread.join(timeout=3)
    # User requested viewing the prepared look; leave this session's look enabled.
    look(True)
rows=list(csv.DictReader((OUT/'telemetry.csv').open()));result={'scope':'static 25% LUT only; no continuous capture or NPU analysis','phases':{}}
for item in manifest:
    label=item['label'];frames=[float(r['frametime_ms']) for r in csv.DictReader((OUT/(label+'.csv')).open()) if float(r['frametime_ms'])>0]
    if len(frames)<100:raise RuntimeError('Insufficient game samples')
    samples=[r for r in rows if r['phase']==label and float(r['time'])>item['start']+5]
    if any(r['battery_status']!='Discharging' or r['tdp']!='20' for r in samples):raise RuntimeError('Power conditions changed')
    d={'samples':len(frames),'fps_from_mean_sampled_frametime':1000/statistics.mean(frames),'p95_sampled_frametime_ms':sorted(frames)[int((len(frames)-1)*.95)]}
    if stream:
        elapsed=item['end']-item['start'];d['coverage_ratio']=sum(frames)/1000/elapsed
        d['presentation_events_per_second']=len(frames)/elapsed
        if not .95<d['coverage_ratio']<1.05:raise RuntimeError('Presentation coverage insufficient')
    for key in ['cpu_percent','gpu_busy','apu_w','battery_w','gpu_mhz']:
        x=[float(r[key]) for r in samples if r[key]!=''];d[key]={'mean':statistics.mean(x),'stddev':statistics.pstdev(x)}
    result['phases'][label]=d
result['limitations']=['Event-driven presentation stream with coverage validation' if stream else '20Hz frametime sampling, not a complete frame trace','Battery readings are smoothed and correlated','No periodic NPU analysis or thumbnail capture included']
(OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
