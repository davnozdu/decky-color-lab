"""Gamescope SDR looks, per-display presets and optional asynchronous neural analysis."""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import pwd
import resource
import subprocess
import copy
import re
import time
import decky

PRESETS = {
 'cinema': {'label':'Кино','strength':25,'black':4,'contrast':.12,'interval':0},
 'game': {'label':'Игры','strength':25,'black':6,'contrast':.18,'interval':0},
 'soft': {'label':'Мягкий','strength':10,'black':0,'contrast':0,'interval':5},
 'black': {'label':'Глубокий чёрный','strength':20,'black':20,'contrast':.12,'interval':5},
 'hdr': {'label':'Псевдо-HDR · SDR','strength':30,'black':10,'contrast':.5,'interval':5},
}

class Plugin:
 async def _main(self):
    self.root=Path(__file__).resolve().parent
    self.home=Path(getattr(decky,'DECKY_USER_HOME','/home/davnozdu'))
    self.user=pwd.getpwnam(self.home.name)
    self.data=self.home/'homebrew/data/Decky Color Lab';self.data.mkdir(parents=True,exist_ok=True)
    if os.geteuid()==0:os.chown(self.data,self.user.pw_uid,self.user.pw_gid)
    self.work_root=Path(f'/run/user/{self.user.pw_uid}')/'decky-color-lab';self.work_root.mkdir(mode=0o700,exist_ok=True)
    if os.geteuid()==0:os.chown(self.work_root,self.user.pw_uid,self.user.pw_gid)
    self.last_saved=0;self.last_preferences=''
    self.settings_file=self.data/'settings.json'
    self.settings={'enabled':True,'auto':True,'profiles':{},'weights':[1.5703125,.0341796875,-.244140625]}
    try:self.settings.update(json.loads(self.settings_file.read_text()))
    except (OSError,ValueError):pass
    self.settings.setdefault('app_profiles',{})
    self.weights=self.settings['weights']
    self.lock=asyncio.Lock();self.analysis_lock=asyncio.Lock();self.analyzer=None
    self.analyzer_model=None;self.last_error='';self.last_analysis=None;self.analysis_ms=None;self.analysis_cpu_ms=None;self.capture_ms=None;self.cycle_ms=None;self.cycle_cpu_ms=None;self.lut_cpu_ms=0;self.waiting=False;self.busy=False
    self.active_display=await asyncio.to_thread(self._display)
    self.active_app=await asyncio.to_thread(self._application)
    self.weights=self._profile()[0].get('weights',self.weights);await self._apply();self.task=asyncio.create_task(self._watch())

 def _display(self):
    candidates=[]
    for path in Path('/sys/class/drm').glob('card*-*'):
      try:
        if (path/'status').read_text().strip()!='connected':continue
        edid=(path/'edid').read_bytes();internal='eDP' in path.name
        name='Встроенный экран' if internal else path.name.split('-',1)[-1]
        for offset in range(54,min(126,len(edid)),18):
          d=edid[offset:offset+18]
          if len(d)==18 and d[:4]==b'\0\0\0\xfc':
            label=d[5:].decode('ascii','ignore').strip('\x00\n ')
            if label:name=label
        candidates.append({'key':hashlib.sha256(edid or path.name.encode()).hexdigest()[:16],
          'name':name,'internal':internal,'active':(path/'enabled').read_text().strip()=='enabled'})
      except OSError:continue
    active=[x for x in candidates if x['active']]
    return next((x for x in active if not x['internal']),next(iter(active or candidates),
      {'key':'unknown','name':'Gamescope','internal':True,'active':True}))

 def _application(self):
    try:
      result=subprocess.run(self._as_user([str(self.root/'bin/app-info')]),capture_output=True,timeout=2)
      lines=result.stdout.decode(errors='replace').splitlines();app_id=int(lines[0])
      if app_id in [0,769]:return {'key':'steam','name':'Steam','id':769}
      name=lines[1] if len(lines)>1 else f'Приложение {app_id}'
      steam_game=False
      for steam in [self.home/'.local/share/Steam',self.home/'.steam/steam']:
        manifest=steam/f'steamapps/appmanifest_{app_id}.acf'
        if manifest.exists():
          steam_game=True
          match=re.search(r'"name"\s+"([^"\n]+)"',manifest.read_text(errors='replace'))
          if match:name=match.group(1)
          break
      return {'key':f'steam:{app_id}','name':name[:100],'id':app_id,'steam_game':steam_game}
    except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):
      return {'key':'steam','name':'Steam','id':769}

 def _work(self):
    p,_=self._profile();token=self.active_display['key']+self.active_app['key']+p['model']+p['engines'][p['model']]
    path=self.work_root/hashlib.sha256(token.encode()).hexdigest()[:16];path.mkdir(mode=0o700,exist_ok=True)
    if os.geteuid()==0:os.chown(path,self.user.pw_uid,self.user.pw_gid)
    return path

 VIDEO_PLAYERS=re.compile(r'\b(vlc|mpv|kodi|jellyfin|plex|plezy|emby|stremio|celluloid|haruna|smplayer|totem|'
   r'media ?player|netflix|youtube|twitch|prime video|disney\+|hbo|crunchyroll|кинопоиск|okko|ivi)\b',re.I)
 BROWSERS=re.compile(r'\b(firefox|chromium|google chrome|brave|microsoft edge|vivaldi)\b',re.I)

 # applied when an app is first seen as a video player, or when the user sets the type manually
 KIND_DEFAULTS={
   'video':{'kind':'video','preset':'cinema','overrides':{},'enabled':True,'auto':True,'tracking':True,'model':'hdr'},
   'game':{'kind':'game','preset':'game','overrides':{},'tracking':False,'model':'adaptive'},
 }

 def _is_video_app(self,app):
    """Players/streaming apps by name; browsers only for non-Steam shortcuts (games keep 'game')."""
    if app['key']=='steam':return False
    name=app.get('name','')
    if app.get('steam_game'):return bool(re.search(r'\b(vlc|mpv|kodi|jellyfin|plex|plezy|stremio)\b',name,re.I))
    return bool(self.VIDEO_PLAYERS.search(name) or self.BROWSERS.search(name))

 def _profile(self):
    profiles=self.settings['app_profiles'].setdefault(self.active_display['key'],{})
    if self.active_app['key'] not in profiles:
      old=self.settings['profiles'].get(self.active_display['key'],{})
      profiles[self.active_app['key']]=copy.deepcopy(old) if self.active_app['key']!='steam' else {}
      if self._is_video_app(self.active_app):
        # first time a movie/video player is focused: dynamic cinema look with auto analysis
        profiles[self.active_app['key']].update(copy.deepcopy(self.KIND_DEFAULTS['video']))
    p=profiles[self.active_app['key']];p.setdefault('preset','game');p.setdefault('overrides',{})
    p.setdefault('enabled',self.settings['enabled'] if self.active_app['key']!='steam' else False)
    p.setdefault('auto',self.settings['auto'] if self.active_app['key']!='steam' else False)
    p.setdefault('kind','game');p.setdefault('tracking',p['kind']=='video')
    if p.get('model') not in ['adaptive','hdr']:p['model']='adaptive'
    hdr_default='npu' if (self.home/'AsusNPU/hdr-probe/npu-tested.json').exists() else 'cpu'
    p.setdefault('engines',{'adaptive':'npu','hdr':hdr_default})
    for key,default in [('adaptive','npu'),('hdr',hdr_default)]:
      if p['engines'].get(key) not in ['cpu','npu']:p['engines'][key]=default
    if p.get('preset') not in PRESETS:p['preset']='game'
    values=dict(PRESETS[p['preset']]);values.update(p.get('overrides',{}));return p,values

 def _save(self):
    self.settings['weights']=self.weights
    self._profile()[0]['weights']=self.weights
    preferences_data=copy.deepcopy(self.settings);preferences_data.pop('weights',None)
    for apps in preferences_data.get('app_profiles',{}).values():
      for profile in apps.values():profile.pop('weights',None)
    preferences=json.dumps(preferences_data,sort_keys=True)
    now=time.monotonic()
    if preferences==self.last_preferences and now-self.last_saved<60:return
    self.last_preferences=preferences;self.last_saved=now
    tmp=self.settings_file.with_suffix('.tmp');tmp.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2)+'\n');tmp.replace(self.settings_file)

 def _as_user(self,args):
    return (['runuser','-u',self.user.pw_name,'--'] if os.geteuid()==0 else [])+[
      'env','-u','LD_LIBRARY_PATH','-u','LD_PRELOAD','-u','PYTHONHOME','-u','PYTHONPATH',f'XDG_RUNTIME_DIR=/run/user/{self.user.pw_uid}','WAYLAND_DISPLAY=gamescope-0','DISPLAY=:0']+list(args)

 async def _run(self,args,timeout=15):
    p=await asyncio.create_subprocess_exec(*self._as_user(args),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:out,err=await asyncio.wait_for(p.communicate(),timeout)
    except asyncio.TimeoutError:p.kill();await p.wait();raise RuntimeError('Операция заняла слишком много времени')
    if p.returncode:raise RuntimeError(err.decode(errors='replace')[-250:] or 'Ошибка применения профиля')
    return out.decode(errors='replace')

 def _cube(self,values):
    n=33**3;s=max(0,min(100,float(values['strength'])))/100
    black=max(0,min(30,float(values['black'])))/100;c=float(values['contrast'])
    p,_=self._profile();work=self._work()
    path=work/'active.cube';tmp=path.with_suffix('.tmp')
    hdr_path=work/'hdr-current.bin'
    if not hdr_path.exists():hdr_path=self.root/'assets/hdr-default.bin'
    args=[str(self.root/'bin/lut-write'),str(self.root/'assets/basis-luts.bin'),str(hdr_path) if p['model']=='hdr' else '-',
      *map(str,self.weights),str(s*100),str(black*100),str(c),str(tmp)]
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    result=subprocess.run(self._as_user(args),capture_output=True,timeout=5)
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    self.lut_cpu_ms=1000*(after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-200:])
    tmp.replace(path)
    if os.geteuid()==0:os.chown(path,self.user.pw_uid,self.user.pw_gid)
    return path

 async def _apply(self):
    p,values=self._profile()
    if p['enabled']:
      path=await asyncio.to_thread(self._cube,values)
      await self._run(['gamescopectl','set_look',str(path)])
    else:
      # Invalid/empty cube clears only g22; native PQ looks remain untouched.
      await self._run(['gamescopectl','set_look','/dev/null'])
    await asyncio.to_thread(self._save)

 async def get_state(self):
    p,v=self._profile()
    try:battery=round(int(Path('/sys/class/power_supply/BAT0/power_now').read_text())/1e6,1)
    except (OSError,ValueError):battery=None
    engine=p['engines'][p['model']]
    engine_label='CPU' if engine=='cpu' else 'CPU + NPU · эксперимент' if p['model']=='hdr' else 'CPU + NPU'
    return {'enabled':p['enabled'],'auto':p['auto'],'preset':p['preset'],'kind':p['kind'],'tracking':p['tracking'],
      'strength':v['strength'],'black':v['black'],'display':self.active_display,'application':self.active_app,'busy':self.busy,'waiting':self.waiting,
      'last_error':self.last_error,'last_analysis':self.last_analysis,'analysis_ms':self.analysis_ms,'analysis_cpu_ms':self.analysis_cpu_ms,'capture_ms':self.capture_ms,'cycle_ms':self.cycle_ms,'cycle_cpu_ms':self.cycle_cpu_ms,
      'interval':v['interval'],'interval_effective':self._interval(v),'battery_w':battery,'model_id':p['model'],'model':(f'HDRTVNet++ AGCM → SDR · {engine_label}' if p['model']=='hdr' else f'Image-Adaptive-3DLUT · {engine_label}'),'hdr_available':True,'engine':engine,'hdr_npu_available':(self.home/'AsusNPU/hdr-probe/npu-tested.json').exists(),'capture':'PipeWire · без скриншотов'}

 async def configure(self,changes):
    async with self.lock:
      if not isinstance(changes,dict):raise ValueError('Неверные настройки')
      p,_=self._profile()
      if 'kind' in changes:
        if changes['kind'] not in self.KIND_DEFAULTS:raise ValueError('Неизвестный тип приложения')
        if self.active_app['key']=='steam':raise ValueError('Тип задаётся для запущенного приложения, не для меню Steam')
        if p.get('model')!=self.KIND_DEFAULTS[changes['kind']]['model']:await self._stop_analyzer()
        p.update(copy.deepcopy(self.KIND_DEFAULTS[changes['kind']]));self.last_analysis=None;self.analysis_ms=None
      for key in ['enabled','auto','tracking']:
        if key in changes:
          if not isinstance(changes[key],bool):raise ValueError('Неверный переключатель')
          p[key]=changes[key]
      if 'model_id' in changes:
        if changes['model_id'] not in ['adaptive','hdr']:raise ValueError('Неизвестная модель')
        if p['model']!=changes['model_id']:
          await self._stop_analyzer();p['model']=changes['model_id'];self.last_analysis=None;self.analysis_ms=None
      if 'engine' in changes:
        if changes['engine'] not in ['cpu','npu']:raise ValueError('Неизвестный исполнитель')
        if p['model']=='hdr' and changes['engine']=='npu' and not (self.home/'AsusNPU/hdr-probe/npu-tested.json').exists():raise ValueError('NPU-вариант ещё не проверен')
        if p['engines'][p['model']]!=changes['engine']:
          await self._stop_analyzer();p['engines'][p['model']]=changes['engine'];self.last_analysis=None;self.analysis_ms=None
      if 'preset' in changes:
        if changes['preset'] not in PRESETS:raise ValueError('Неизвестная предустановка')
        p['preset']=changes['preset'];p['overrides']={}
      if 'interval' in changes:
        if changes['interval'] not in [0,1,2,5,10,15,30,60]:raise ValueError('Неизвестный интервал')
        p.setdefault('overrides',{})['interval']=changes['interval']
      for key,maximum in [('strength',100),('black',30)]:
        if key in changes:
          value=changes[key]
          if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=maximum:raise ValueError('Значение вне диапазона')
          p.setdefault('overrides',{})[key]=round(value)
      await self._apply();self.last_error=''
      if not p['enabled'] or not p['auto']:await self._stop_analyzer()
    return await self.get_state()

 async def _ensure_analyzer(self):
    p,_=self._profile();model=p['model']
    engine=p['engines'][model]
    if self.analyzer and self.analyzer.returncode is None and self.analyzer_model==(model,str(self._work()),engine):return
    await self._stop_analyzer();self.analyzer_model=(model,str(self._work()),engine)
    # NPU DMA buffers need more locked memory than Decky's 8 MiB service default.
    if os.geteuid()==0:
      soft,hard=resource.getrlimit(resource.RLIMIT_MEMLOCK)
      target=512*1024*1024
      if soft!=resource.RLIM_INFINITY and soft<target:
        resource.setrlimit(resource.RLIMIT_MEMLOCK,(target,hard if hard==resource.RLIM_INFINITY else max(hard,target)))
    runtime=self.home/'AsusNPU/framegen-probe/runtime.sh';python=self.home/'AsusNPU/sesr-env/bin/python'
    cmd=['nice','-n','10','bash','-c','source "$1"; shift; exec "$@"','color-lab',str(runtime),str(python),
      str(self.root/'bin/analyzer.py'),str(self.home/'AsusNPU'),str(self._work()),model,engine,str(self.active_app['id'] if self.active_app['key']!='steam' else 0),
      str(self.work_root/('frame-'+hashlib.sha256((self.active_display['key']+self.active_app['key']).encode()).hexdigest()[:16]+'.rgb'))]
    self.analyzer=await asyncio.create_subprocess_exec(*self._as_user(cmd),stdin=asyncio.subprocess.PIPE,
      stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    response=json.loads(await asyncio.wait_for(self.analyzer.stdout.readline(),75))
    if not response.get('ready'):raise RuntimeError(response.get('error','Анализатор недоступен'))

 AUTO_STEPS=((.15,10),(.5,2),(float('inf'),1))  # drift below threshold -> seconds between analyses

 def _interval(self,values):
    """Seconds between scheduled analyses; interval 0 = automatic from recent picture drift."""
    if values['interval']:return values['interval']
    drift=getattr(self,'drift',0.)
    return next(seconds for limit,seconds in self.AUTO_STEPS if drift<limit)

 async def analyze(self,force=True,probe=False):
    if self.analysis_lock.locked():return await self.get_state()
    async with self.analysis_lock:
      quiet=False;self.busy=True;started=time.monotonic();cpu_started=time.process_time();worker_cpu=0;lut_cpu=0;model_id=self._profile()[0]['model'];app_key=self.active_app['key'];display_key=self.active_display['key'];engine_id=self._profile()[0]['engines'][model_id]
      try:
        await self._ensure_analyzer()
        self.analyzer.stdin.write((json.dumps({'force':force,'probe':probe})+'\n').encode());await self.analyzer.stdin.drain()
        response=json.loads(await asyncio.wait_for(self.analyzer.stdout.readline(),20))
        if response.get('error'):raise RuntimeError(response['error'])
        if 'delta' in response:
          # smoothed picture drift since the last analysis (1.0 ~ scene-cut threshold)
          self.drift=.5*getattr(self,'drift',0.)+.5*float(response['delta'])
        if probe and response.get('stable'):
          quiet=True;return await self.get_state()
        self.waiting=response.get('waiting',False);self.capture_ms=response.get('capture_ms');worker_cpu=response.get('analysis_total_cpu_ms',0)
        if not response.get('stable'):
          if (model_id,app_key,display_key,engine_id)!=(self._profile()[0]['model'],self.active_app['key'],self.active_display['key'],self._profile()[0]['engines'][self._profile()[0]['model']]):return await self.get_state()
          if model_id=='hdr':
            if response.get('lut_file')!='hdr-current.bin':raise RuntimeError('Нет HDR-таблицы')
          else:
            new=response['weights']
            if len(new)!=3 or any(not math.isfinite(x) or abs(x)>10 for x in new):raise RuntimeError('Недопустимые коэффициенты')
            alpha=.8 if response.get('scene_cut') else .35 if force else .2
            self.weights=[a*(1-alpha)+b*alpha for a,b in zip(self.weights,new)]
          self.analysis_ms=response.get('model_ms');self.analysis_cpu_ms=response.get('model_cpu_ms');self.last_analysis=time.time()
          async with self.lock:
            if self._profile()[0]['enabled']:
              await self._apply();lut_cpu=self.lut_cpu_ms
        self.last_error=''
      except Exception as error:
        self.last_error=str(error)[:220];decky.logger.error('Color analysis: %s',error);await self._stop_analyzer()
      finally:
        self.busy=False
        if not quiet:
          self.cycle_ms=(time.monotonic()-started)*1000;self.cycle_cpu_ms=(time.process_time()-cpu_started)*1000+worker_cpu+lut_cpu
    return await self.get_state()

 async def _stop_analyzer(self):
    process=self.analyzer;self.analyzer=None
    if process and process.returncode is None:
      if process.stdin:process.stdin.close()
      try:await asyncio.wait_for(process.wait(),3)
      except asyncio.TimeoutError:process.kill();await process.wait()

 async def _watch(self):
    next_analysis=time.monotonic()+10;next_display=0;next_app=0
    try:
      while True:
        await asyncio.sleep(.5);now=time.monotonic()
        display=await asyncio.to_thread(self._display) if now>=next_display else self.active_display
        if now>=next_display:next_display=now+5
        app=await asyncio.to_thread(self._application) if now>=next_app else self.active_app
        if now>=next_app:next_app=now+1
        if (display['key'],app['key'])!=(self.active_display['key'],self.active_app['key']):
          async with self.lock:
            await self._stop_analyzer();self.active_display=display;self.active_app=app
            self.weights=self._profile()[0].get('weights',self.settings['weights']);self.last_analysis=None;self.analysis_ms=None;await self._apply()
            next_analysis=now+2
        p,v=self._profile()
        if p['enabled'] and p['auto'] and not self.busy:
          if time.monotonic()>=next_analysis:
            await self.analyze(force=False);next_analysis=time.monotonic()+self._interval(v)
          elif p.get('tracking') or not v['interval']:
            # cheap scene check ~2x/s; the model only runs (and the timer restarts) on a scene cut
            before=self.last_analysis
            await self.analyze(force=False,probe=True)
            if self.last_analysis!=before:next_analysis=time.monotonic()+self._interval(v)
            elif self.last_analysis:
              # drift grew -> bring the next scheduled analysis forward (auto interval)
              due=time.monotonic()+max(0.,self._interval(v)-(time.time()-self.last_analysis))
              next_analysis=min(next_analysis,due)
    except asyncio.CancelledError:pass

 async def _unload(self):
    if getattr(self,'task',None):self.task.cancel()
    await self._stop_analyzer()

 async def _uninstall(self):
    await self._run(['gamescopectl','set_look','/dev/null'])
