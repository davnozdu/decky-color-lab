"""CPU-only verification of HDRTVNet++ AGCM export, tiling and SDR preview.
Uses the published network/checkpoint directly as reference. No NPU provider.
"""
from pathlib import Path
import ast,importlib.util,json,sys
import numpy as np,torch,onnxruntime as ort
from PIL import Image
R=Path(__file__).resolve().parent;W=R.parent;sys.path.insert(0,str(W/'decky-color-lab/bin'));from hdr_tonemap import to_sdr
source=W/'framegen-probe/hf-candidates/HDRTVNet-plus-source'
s=importlib.util.spec_from_file_location('hdr_arch',source/'codes/models/modules/Condition_arch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
torch.set_num_threads(1);net=m.ConditionNet(cond_c=6).eval();net.load_state_dict(torch.load(source/'pretrained_models/AGCM.pth',weights_only=True,map_location='cpu'))
so=ort.SessionOptions();so.intra_op_num_threads=so.inter_op_num_threads=1
classifier=ort.InferenceSession(str(R/'hdr-condition.onnx'),so,providers=['CPUExecutionProvider']);pointwise=ort.InferenceSession(str(R/'hdr-pointwise.onnx'),so,providers=['CPUExecutionProvider'])
b,g,r=np.meshgrid(*[np.linspace(0,1,33,dtype=np.float32)]*3,indexing='ij');grid=np.stack([r,g,b]).reshape(3,-1);n=33**3
assert np.array_equal(grid,np.fromfile(R/'grid-unpadded.bin',np.float32).reshape(3,n))
cases={f'gray-{t}':np.full((256,256,3),t,np.float32) for t in [0,.01,.03125,.0625,.125,.25,.5,.75,1]}
for name,rgb in [('red',[1,0,0]),('green',[0,1,0]),('blue',[0,0,1]),('cyan',[0,1,1]),('yellow',[1,1,0]),('magenta',[1,0,1])]:cases[name]=np.broadcast_to(np.array(rgb,np.float32),(256,256,3)).copy()
a=np.linspace(0,1,256,dtype=np.float32);cases['gray-ramp']=np.broadcast_to(a[None,:,None],(256,256,3)).copy();cases['rgb-ramps']=np.stack(list(np.meshgrid(a,a,indexing='xy'))+[np.broadcast_to(a,(256,256))],axis=-1)
cases['noise']=np.random.default_rng(42).random((256,256,3),dtype=np.float32);cases['dark-noise']=cases['noise']*.04
for f in [W/'motion-probe/game-before.png',W/'color-probe/npu-look-preview.png']:
 cases[f.name]=np.asarray(Image.open(f).convert('RGB').resize((256,256)),np.float32)/255
class FixedCondition(torch.nn.Module):
 def __init__(self,features):super().__init__();self.register_buffer('features',torch.from_numpy(features).reshape(1,6,1,1))
 def forward(self,image):return self.features
rows=[];gray_ids=np.arange(33)*(1089+33+1)
for name,image in cases.items():
 x=np.ascontiguousarray(image.transpose(2,0,1)[None]);features=classifier.run(None,{'image':x})[0];out=np.zeros((3,n),np.float32)
 for start in range(0,n,4096):
  size=min(4096,n-start);tile=np.zeros((3,4096),np.float32);tile[:,:size]=grid[:,start:start+size]
  value=pointwise.run(None,{'grid':tile.reshape(1,3,64,64),'features':features})[0].reshape(3,4096)
  out[:,start:start+size]=value[:,:size]
 with torch.no_grad():ref=net([torch.from_numpy(grid.reshape(1,3,33,1089)),torch.from_numpy(x)])[0].numpy().reshape(3,n)
 error=float(abs(out-ref).max());assert np.isfinite(ref).all(),name
 original_classifier=net.classifier
 with torch.no_grad():reference_features=original_classifier(torch.from_numpy(x)).numpy().reshape(1,6)
 feature_error=float(abs(features-reference_features).max())
 net.classifier=FixedCondition(features)
 with torch.no_grad():same_features=net([torch.from_numpy(grid.reshape(1,3,33,1089)),torch.from_numpy(x)])[0].numpy().reshape(3,n)
 net.classifier=original_classifier
 tile_error=float(abs(out-same_features).max());assert tile_error<3e-6,(name,tile_error)
 sdr=to_sdr(out);assert np.isfinite(sdr).all() and sdr.min()>=0 and sdr.max()<=1
 grey=sdr[:,gray_ids]
 rows.append({'case':name,'max_model_difference':error,'feature_error':feature_error,'tile_error_same_features':tile_error,'pq_range':[float(out.min()),float(out.max())],'sdr_black':sdr[:,0].tolist(),'sdr_white':sdr[:,-1].tolist(),'dark_gray_max_channel_spread':float(np.ptp(grey[:,:5],axis=0).max()),'clipped_sdr_fraction':float(np.mean(sdr>=1))})
# Independent analytic PQ inputs exercise the display conversion, not the network.
nits=np.r_[0,np.geomspace(.0001,10000,4096)]
a=(nits/10000)**(2610/16384);pq=((3424/4096+2413/128*a)/(1+2392/128*a))**(2523/32)
neutral=to_sdr(np.repeat(pq[None,:],3,axis=0));assert np.ptp(neutral,axis=0).max()<1e-6;assert np.diff(neutral.mean(0)).min()>=-1e-7;assert neutral[:,0].max()==0
high=neutral[:,nits>1000];highlight_clips=bool(np.all(high==1))
# Crop behavior including fully black frames is checked without executing the worker.
module=ast.parse((W/'decky-color-lab/bin/analyzer.py').read_text());fn=next(n for n in ast.walk(module) if isinstance(n,ast.FunctionDef) and n.name=='content_crop');scope={'np':np};exec(compile(ast.Module(body=[fn],type_ignores=[]),'crop','exec'),scope)
for image in [np.zeros((256,256,3),np.float32),np.ones((256,256,3),np.float32)]:
 cropped,_=scope['content_crop'](image);assert np.array_equal(image,cropped)
image=np.full((256,256,3),.5,np.float32);image[:32]=image[-32:]=0;cropped,bars=scope['content_crop'](image);assert np.allclose(cropped,.5);assert abs(bars-.25)<1e-7
report={'scope':'CPU only; original AGCM vs split ONNX; no NPU run; HDR code unchanged','cases':len(rows),'max_model_difference':max(r['max_model_difference'] for r in rows),'max_tile_error_same_features':max(r['tile_error_same_features'] for r in rows),'max_image_fixture_error':max(r['max_model_difference'] for r in rows if r['case'].endswith('.png')),'pq_neutral_and_monotone':True,'black_white_letterbox_tests':True,'sdr_preview_clips_neutral_above_1000_nits':highlight_clips,'saved_npu_precision_results':json.loads((R/'tiled-comparison.json').read_text()),'results':rows}
(R/'hdr-model-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['results','saved_npu_precision_results']},indent=2))
