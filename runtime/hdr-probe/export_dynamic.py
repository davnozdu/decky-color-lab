"""Prevent ORT folding the RGB lattice into a large 64-channel constant activation."""
from pathlib import Path
import importlib.util
import numpy as np,torch
from torch import nn
R=Path(__file__).resolve().parent
UP=R.parent/'framegen-probe/hf-candidates/HDRTVNet-plus-source'
s=importlib.util.spec_from_file_location('arch',UP/'codes/models/modules/Condition_arch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Norm(nn.Module):
 def __init__(self,n):super().__init__();self.weight=n.weight;self.bias=n.bias;self.eps=n.eps
 def forward(self,x):
  d=x-x.mean((2,3),keepdim=True);return d/torch.sqrt((d*d).mean((2,3),keepdim=True)+self.eps)*self.weight[None,:,None,None]+self.bias[None,:,None,None]
class Model(nn.Module):
 def __init__(self):
  super().__init__();self.net=m.ConditionNet(cond_c=6).eval();self.net.load_state_dict(torch.load(UP/'pretrained_models/AGCM.pth',weights_only=True,map_location='cpu'))
  for k,n in enumerate(self.net.classifier.model):
   if isinstance(n,nn.InstanceNorm2d):self.net.classifier.model[k]=Norm(n)
 def forward(self,image,grid):return self.net([grid,image])[0].reshape(1,3,-1)[:,:,:33**3]
torch.set_num_threads(1);net=Model().eval();b,g,r=np.meshgrid(*[np.linspace(0,1,33,dtype=np.float32)]*3,indexing='ij')
grid=np.pad(np.stack([r,g,b]).reshape(3,-1),((0,0),(0,192*192-33**3))).reshape(1,3,192,192);grid.tofile(R/'grid.bin')
x=torch.from_numpy(np.fromfile(R/'input.bin',np.float32).reshape(1,3,256,256));y=torch.from_numpy(grid)
with torch.no_grad():out=net(x,y).numpy()
ref=np.fromfile(R/'reference.bin',np.float32).reshape(out.shape);np.testing.assert_allclose(out,ref,atol=1e-6,rtol=1e-5)
torch.onnx.export(net,(x,y),str(R/'hdr-lattice-dynamic.onnx'),input_names=['image','grid'],output_names=['hdr_lut'],opset_version=17,dynamo=False)
print('Dynamic grid exported; CPU max error',abs(out-ref).max())
