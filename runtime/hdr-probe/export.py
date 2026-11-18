"""HDRTVNet++ AGCM on a fixed RGB lattice. No local enhancement stage.
Upstream MIT weights; fixed 256x256 condition is an experimental preprocessing choice.
"""
from pathlib import Path
import importlib.util,json,shutil
import numpy as np
import torch
from torch import nn
from PIL import Image
ROOT=Path(__file__).resolve().parent
UP=ROOT.parent/'framegen-probe/hf-candidates/HDRTVNet-plus-source'
s=importlib.util.spec_from_file_location('hdr_arch',UP/'codes/models/modules/Condition_arch.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ExplicitNorm(nn.Module):
 def __init__(self,old):
  super().__init__();self.weight=old.weight;self.bias=old.bias;self.eps=old.eps
 def forward(self,x):
  d=x-x.mean((2,3),keepdim=True)
  return d/torch.sqrt((d*d).mean((2,3),keepdim=True)+self.eps)*self.weight[None,:,None,None]+self.bias[None,:,None,None]
class Lattice(nn.Module):
 def __init__(self,net):
  super().__init__();self.net=net
  b,g,r=np.meshgrid(*[np.linspace(0,1,33,dtype=np.float32)]*3,indexing='ij')
  self.register_buffer('grid',torch.from_numpy(np.pad(np.stack([r,g,b]).reshape(3,-1),((0,0),(0,192*192-33**3))).reshape(1,3,192,192)))
 def forward(self,image):return self.net([self.grid,image])[0].reshape(1,3,-1)[:,:,:33**3]
torch.set_num_threads(1)
net=m.ConditionNet(cond_c=6).eval()
w=torch.load(UP/'pretrained_models/AGCM.pth',map_location='cpu',weights_only=True)
net.load_state_dict(w,strict=True)
image=Image.open(ROOT.parent/'motion-probe/game-before.png').convert('RGB').resize((256,256),Image.Resampling.BICUBIC)
x=torch.from_numpy((np.asarray(image,dtype=np.float32)/255).transpose(2,0,1).copy()[None])
model=Lattice(net).eval()
with torch.no_grad():original=model(x).numpy()
for key,layer in enumerate(net.classifier.model):
 if isinstance(layer,nn.InstanceNorm2d):net.classifier.model[key]=ExplicitNorm(layer)
with torch.no_grad():out=model(x).numpy()
np.testing.assert_allclose(out,original,rtol=2e-4,atol=2e-5)
torch.onnx.export(model,(x,),str(ROOT/'hdr-lattice.onnx'),input_names=['image'],output_names=['hdr_lut'],opset_version=17,dynamo=False)
x.numpy().tofile(ROOT/'input.bin');out.tofile(ROOT/'reference.bin')
shutil.copyfile(UP/'LICENSE',ROOT/'LICENSE.upstream')
report={'parameters':sum(p.numel() for p in model.parameters()),'shape':list(out.shape),'range':[float(out.min()),float(out.max())],'norm_rewrite_error':float(np.max(np.abs(original-out))),'scope':'HDRTVNet++ AGCM global stage only, PQ BT.2020 output; fixed 256x256 condition; 33^3 LUT approximates pointwise network between grid points'}
(ROOT/'preparation.json').write_text(json.dumps(report,indent=2));print(report)
