"""Render an offline NPU-selected color look. Does not change the live game."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

p = argparse.ArgumentParser()
p.add_argument('--weights', type=Path, required=True)
p.add_argument('--strength', type=float, default=.25)
args = p.parse_args()
if not 0 <= args.strength <= 1: raise SystemExit('Strength must be 0..1')
root = Path(__file__).resolve().parent
weights = np.fromfile(args.weights, np.float32)
reference = np.fromfile(root/'reference.bin', np.float32)
if weights.size != 3 or not np.isfinite(weights).all(): raise SystemExit('Invalid coefficients')
if np.max(np.abs(weights-reference)) > .1: raise SystemExit('NPU coefficients differ too much; inspect before preview')
basis = np.load(root/'basis-luts.npy')
axis = np.linspace(0,1,33,dtype=np.float32)
bb,gg,rr = np.meshgrid(axis,axis,axis,indexing='ij')
identity = np.stack([rr,gg,bb])
selected = np.tensordot(weights,basis,axes=(0,0))
lut = np.clip(identity*(1-args.strength)+selected*args.strength,0,1).astype(np.float32)
cube = root/'npu-look.cube'
with cube.open('w') as f:
    f.write('TITLE "Experimental NPU-selected SDR color look"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    for row in lut.transpose(1,2,3,0).reshape(-1,3):
        f.write('%.7f %.7f %.7f\n'%tuple(row))
image = Image.open(root.parent/'motion-probe/game-before.png').convert('RGB')
pixels = np.asarray(image,np.float32)/255
grid = torch.from_numpy(pixels*2-1)[None,None]
torch.set_num_threads(1)
def apply(table):
    out = F.grid_sample(torch.from_numpy(table)[None],grid,mode='bilinear',padding_mode='border',align_corners=True)
    return out[0,:,0].permute(1,2,0).numpy()
np.testing.assert_allclose(apply(identity),pixels,atol=1e-5)
result = np.clip(np.rint(apply(lut)*255),0,255).astype(np.uint8)
Image.fromarray(result).save(root/'npu-look-preview.png')
comparison = Image.new('RGB',(image.width*2,image.height))
comparison.paste(image,(0,0));comparison.paste(Image.fromarray(result),(image.width,0))
comparison.save(root/'comparison-original-left-npu-right.jpg',quality=95)
(root/'look-metadata.json').write_text(json.dumps({'coefficients':weights.tolist(),
    'cpu_reference':reference.tolist(),'max_coefficient_error':float(np.max(np.abs(weights-reference))),
    'strength':args.strength,'lut_size':33,'scope':'offline SDR tone/color preview; not applied to game, not HDR'},indent=2)+'\n')
print('Created',cube,'and offline preview')
