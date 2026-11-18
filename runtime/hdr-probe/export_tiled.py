"""Exact AGCM split: scene classifier -> six features; pointwise network -> 64² colors.
Evaluating the RGB lattice in nine tiles changes batching only, not learned weights.
"""
from pathlib import Path
import importlib.util
import torch,numpy as np
from torch import nn
R=Path(__file__).resolve().parent;UP=R.parent/'framegen-probe/hf-candidates/HDRTVNet-plus-source'
s=importlib.util.spec_from_file_location('arch',UP/'codes/models/modules/Condition_arch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
torch.set_num_threads(1);net=m.ConditionNet(cond_c=6).eval();net.load_state_dict(torch.load(UP/'pretrained_models/AGCM.pth',weights_only=True,map_location='cpu'))
class Classifier(nn.Module):
 def __init__(self):super().__init__();self.classifier=net.classifier
 def forward(self,image):return self.classifier(image).reshape(1,6)
class Pointwise(nn.Module):
 def __init__(self):
  super().__init__()
  for name in ['conv_first','HRconv','conv_last','cond_scale_first','cond_shift_first','cond_scale_HR','cond_shift_HR','cond_scale_last','cond_shift_last']:setattr(self,name,getattr(net,name))
 def forward(self,grid,features):
  y=self.conv_first(grid);y=torch.relu(y*(1+self.cond_scale_first(features)[:,:,None,None])+self.cond_shift_first(features)[:,:,None,None])
  y=self.HRconv(y);y=torch.relu(y*(1+self.cond_scale_HR(features)[:,:,None,None])+self.cond_shift_HR(features)[:,:,None,None])
  y=self.conv_last(y);return y*(1+self.cond_scale_last(features)[:,:,None,None])+self.cond_shift_last(features)[:,:,None,None]
x=torch.from_numpy(np.fromfile(R/'input.bin',np.float32).reshape(1,3,256,256));classifier=Classifier().eval();pointwise=Pointwise().eval()
with torch.no_grad():features=classifier(x)
b,g,r=np.meshgrid(*[np.linspace(0,1,33,dtype=np.float32)]*3,indexing='ij');all_rgb=np.stack([r,g,b]).reshape(3,-1);all_rgb.tofile(R/'grid-unpadded.bin');n=all_rgb.shape[1];result=np.zeros((3,n),np.float32)
with torch.no_grad():
 for start in range(0,n,4096):
  size=min(4096,n-start);block=np.zeros((3,4096),np.float32);block[:,:size]=all_rgb[:,start:start+size]
  result[:,start:start+size]=pointwise(torch.from_numpy(block.reshape(1,3,64,64)),features).numpy().reshape(3,-1)[:,:size]
ref=np.fromfile(R/'reference.bin',np.float32).reshape(3,n);print('Tile split max error',float(abs(result-ref).max()));np.testing.assert_allclose(result,ref,atol=2e-6,rtol=2e-5)
grid=torch.from_numpy(np.zeros((1,3,64,64),np.float32))
torch.onnx.export(classifier,(x,),str(R/'hdr-condition.onnx'),input_names=['image'],output_names=['features'],opset_version=17,dynamo=False)
torch.onnx.export(pointwise,(grid,features),str(R/'hdr-pointwise.onnx'),input_names=['grid','features'],output_names=['hdr_lut'],opset_version=17,dynamo=False)
