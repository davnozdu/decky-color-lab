"""Persistent native inference and on-demand raw PipeWire frame capture."""
import json,os,subprocess,sys,time,struct,ctypes
from pathlib import Path
import numpy as np
from hdr_tonemap import to_sdr
def useful_adaptive_frame(frame):
 """The photo-trained classifier is unreliable on flat cards and near-black fades."""
 spread=float(frame.std(axis=(0,1)).max())
 luma=float(frame.mean(axis=(0,1))@np.array([.2126,.7152,.0722]))
 return spread>=.01 and not (luma<.03 and spread<.02)
home,data=map(Path,sys.argv[1:3]);model=sys.argv[3];engine=sys.argv[4] if len(sys.argv)>4 else ('cpu' if model=='hdr' else 'npu');app_id=sys.argv[5] if len(sys.argv)>5 else '0';last=None;last_stats=None;process=None;previous_lut=None;capture_process=None
root=home/('hdr-probe' if model=='hdr' else 'color-probe')
log=(data/'native-analysis.log').open('a')
try:
 env=os.environ.copy();env['COLOR_ALLOW_CPU']='1'
 if engine=='cpu':env['COLOR_CPU']='1'
 if model=='hdr' and engine=='npu' and not (root/'npu-tested.json').exists():raise RuntimeError('NPU-модель ещё не проверена')
 tiled=model=='hdr' and (root/'hdr-probe-tiled').exists()
 process=subprocess.Popen([str(root/('hdr-probe-tiled' if tiled else 'hdr-probe' if model=='hdr' else 'color-probe')),
   str(root/('hdr-pointwise.onnx' if tiled else 'hdr-lattice.onnx' if model=='hdr' else 'lut-classifier.onnx')),str(root/'input.bin'),
   str(data/('hdr-native.bin' if model=='hdr' else 'native-first.bin')),str(root/('cache-tiled' if tiled else 'cache')),
   str(root/'bf16-vectorized.json' if tiled else home/'framegen-probe/bf16-config.json'),'0'],cwd=data,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log)
 def native(prefix):
  while True:
   line=process.stdout.readline()
   if not line:raise RuntimeError('Нативный NPU-анализатор завершился')
   text=line.decode(errors='replace').strip()
   if text.startswith(prefix):return text
   log.write(text+'\n');log.flush()
 native('HDR_READY' if model=='hdr' else 'COLOR_READY')
 capture_process=subprocess.Popen([str(Path(__file__).parent/'capture-pw'),'serve',app_id,*([sys.argv[6]] if len(sys.argv)>6 else [])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log)
 if capture_process.stdout.readline()!=b'PW_READY\n':raise RuntimeError('Поток Gamescope недоступен')
 print(json.dumps({'ready':True}),flush=True)
 libc=ctypes.CDLL(None);libc.clock_getcpuclockid.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_int)];libc.clock_getcpuclockid.restype=ctypes.c_int
 child_clocks=[]
 for child in [process,capture_process]:
  clock=ctypes.c_int()
  if libc.clock_getcpuclockid(child.pid,ctypes.byref(clock))!=0:raise RuntimeError('CPU clock unavailable')
  child_clocks.append(clock.value)
 def content_crop(frame,threshold=.06,minimum=96):
  """Drop letterbox/pillarbox bars (rows/columns whose brightest pixel is near black) so movie
  analysis sees only the picture; resize the rest back to 256x256 (separable linear)."""
  luma=frame@np.array([.299,.587,.114],np.float32)
  def span(maxima):
   dark=maxima<threshold
   if dark.all():return 0,len(maxima)
   a=int(np.argmax(~dark));b=len(maxima)-int(np.argmax(~dark[::-1]))
   return (a,b) if b-a>=minimum else (0,len(maxima))
  t,b=span(luma.max(1));l,r=span(luma.max(0))
  if t<6 and 256-b<6 and l<6 and 256-r<6:return frame,0.
  crop=frame[t:b,l:r]
  ys=np.linspace(0,crop.shape[0]-1,256);xs=np.linspace(0,crop.shape[1]-1,256)
  y0=np.floor(ys).astype(int);y1=np.minimum(y0+1,crop.shape[0]-1);fy=(ys-y0)[:,None,None]
  x0=np.floor(xs).astype(int);x1=np.minimum(x0+1,crop.shape[1]-1);fx=(xs-x0)[None,:,None]
  rows=crop[y0]*(1-fy)+crop[y1]*fy
  out=rows[:,x0]*(1-fx)+rows[:,x1]*fx
  return np.ascontiguousarray(out,np.float32),1-(b-t)*(r-l)/(256*256)
 def cpu_total():
  total=time.process_time()
  for clock in child_clocks:
   try:total+=time.clock_gettime(clock)
   except OSError:pass
  return total
 for line in sys.stdin:
  try:
   req=json.loads(line);start=time.monotonic();cpu_start=cpu_total()
   capture_process.stdin.write(b'f');capture_process.stdin.flush()
   def read_exact(n):
    chunks=[];remaining=n
    while remaining:
     part=capture_process.stdout.read(remaining)
     if not part:raise RuntimeError('Поток захвата завершился')
     chunks.append(part);remaining-=len(part)
    return b''.join(chunks)
   size=struct.unpack('<I',read_exact(4))[0]
   if size==0:
    print(json.dumps({'stable':True,'waiting':True,'capture_ms':(time.monotonic()-start)*1000,'analysis_total_cpu_ms':(cpu_total()-cpu_start)*1000}),flush=True);continue
   if size!=256*256*3:raise RuntimeError('Некорректный пакет PipeWire')
   frame=np.frombuffer(read_exact(size),np.uint8).reshape(256,256,3).astype(np.float32)/255
   frame,bars=content_crop(frame)
   capture_ms=(time.monotonic()-start)*1000
   hist=np.concatenate([np.histogram(frame[:,:,c],bins=16,range=(0,1))[0]/(256*256) for c in range(3)])
   stats=np.concatenate([hist,frame.mean((0,1)),frame.std((0,1))])
   scene_cut=last_stats is None or np.abs(stats[:48]-last_stats[:48]).sum()/3>.35 or np.abs(stats[48:]-last_stats[48:]).max()>.12
   stable=last_stats is not None and np.abs(stats[:48]-last_stats[:48]).sum()/3<.08 and np.abs(stats[48:]-last_stats[48:]).max()<.025 and not req.get('force')
   # probe: cheap scene check (capture + histogram only); the model runs only on a scene cut
   if model=='adaptive' and not useful_adaptive_frame(frame):result={'stable':True,'low_information':True,'probe':bool(req.get('probe'))}
   elif stable or (req.get('probe') and not scene_cut):result={'stable':True,'probe':bool(req.get('probe'))}
   else:
    pixels=np.ascontiguousarray(frame.transpose(2,0,1)[None]);process.stdin.write(pixels.tobytes());process.stdin.flush()
    if model=='hdr':
     values=native('HDR_RESULT').split()[1:]
     pq=np.fromfile(data/'hdr-native.bin',np.float32)
     if pq.size!=3*33**3 or not np.isfinite(pq).all():raise RuntimeError('Некорректный выход HDR-модели')
     lut=to_sdr(pq)
     if previous_lut is not None:
      alpha=.8 if scene_cut else .35 if req.get('force') else .2;lut=previous_lut*(1-alpha)+lut*alpha
     previous_lut=lut.copy();tmp=data/'hdr-current.tmp';lut.astype(np.float32).tofile(tmp);tmp.replace(data/'hdr-current.bin')
     result={'lut_file':'hdr-current.bin','model_ms':float(values[0]),'model_cpu_ms':float(values[1])}
    else:
     values=native('COLOR_RESULT').split()[1:]
     result={'weights':[float(x) for x in values[:3]],'model_ms':float(values[3]),'model_cpu_ms':float(values[4])}
    last=frame.copy();last_stats=stats.copy()
   # how much the picture drifted since the last analysed frame (0 = same); drives the auto interval
   result['delta']=0. if last_stats is None else round(float(max(np.abs(stats[:48]-last_stats[:48]).sum()/3/.35,np.abs(stats[48:]-last_stats[48:]).max()/.12)),3)
   result['scene_cut']=bool(scene_cut);result['letterbox']=round(float(bars),3);result['capture_ms']=capture_ms;result['elapsed_ms']=(time.monotonic()-start)*1000;result['analysis_total_cpu_ms']=(cpu_total()-cpu_start)*1000;print(json.dumps(result),flush=True)
  except Exception as error:print(json.dumps({'error':str(error)}),flush=True)
except Exception as error:print(json.dumps({'error':str(error)}),flush=True)
finally:
 if capture_process and capture_process.poll() is None:
  capture_process.stdin.close()
  try:capture_process.wait(timeout=2)
  except subprocess.TimeoutExpired:capture_process.kill();capture_process.wait()
 if process and process.poll() is None:
  process.stdin.close()
  try:process.wait(timeout=3)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 log.close()
