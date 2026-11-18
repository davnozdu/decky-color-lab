"""Export only the 256px LUT classifier, not a full-image HDR network.

Architecture/weights: HuiZeng/Image-Adaptive-3DLUT, Apache-2.0. See LICENSE.upstream.
"""
from pathlib import Path
import json
import numpy as np
import torch
from torch import nn
from PIL import Image

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT.parent / 'framegen-probe/hf-candidates/Image-Adaptive-3DLUT-source'

class ExplicitInstanceNorm(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(channels))
        self.bias = nn.Parameter(torch.zeros(channels))
    def forward(self, x):
        mean = x.mean(dim=(2, 3), keepdim=True)
        centered = x - mean
        variance = (centered * centered).mean(dim=(2, 3), keepdim=True)
        return centered / torch.sqrt(variance + 1e-5) * self.weight[None, :, None, None] + self.bias[None, :, None, None]

class Classifier(nn.Module):
    def __init__(self, explicit):
        super().__init__()
        # Identity replaces upstream resize because input is already 256x256.
        layers = [nn.Identity(), nn.Conv2d(3, 16, 3, 2, 1), nn.LeakyReLU(.2),
                  ExplicitInstanceNorm(16) if explicit else nn.InstanceNorm2d(16, affine=True)]
        for ci, co in [(16, 32), (32, 64), (64, 128), (128, 128)]:
            layers.extend([nn.Conv2d(ci, co, 3, 2, 1), nn.LeakyReLU(.2)])
        layers.append(nn.Conv2d(128, 3, 8))
        self.model = nn.Sequential(*layers)
    def forward(self, x): return self.model(x)

torch.set_num_threads(1)
weights = torch.load(UPSTREAM/'pretrained_models/sRGB/classifier_unpaired.pth', map_location='cpu', weights_only=True)
original, model = Classifier(False).eval(), Classifier(True).eval()
original.load_state_dict(weights, strict=True); model.load_state_dict(weights, strict=True)
image = Image.open(ROOT.parent/'motion-probe/game-before.png').convert('RGB').resize((256,256), Image.Resampling.BILINEAR)
array = (np.asarray(image, np.float32)/255).transpose(2,0,1).copy()[None]
tensor = torch.from_numpy(array)
with torch.no_grad():
    reference = original(tensor)
    actual = model(tensor)
    torch.testing.assert_close(actual, reference, rtol=1e-4, atol=1e-5)
    values = actual.numpy()
array.tofile(ROOT/'input.bin'); values.tofile(ROOT/'reference.bin')
torch.onnx.export(model, (tensor,), str(ROOT/'lut-classifier.onnx'), input_names=['image'],
    output_names=['weights'], opset_version=17, dynamo=False)
lut_state = torch.load(UPSTREAM/'pretrained_models/sRGB/LUTs_unpaired.pth', map_location='cpu', weights_only=True)
np.save(ROOT/'basis-luts.npy', np.stack([lut_state[str(i)]['LUT'].numpy() for i in range(3)]))
report = {'source_commit':'b491f6df64a588864739a157db271e5c848e1805',
    'weights': values.reshape(-1).tolist(), 'classifier_parameters':sum(p.numel() for p in model.parameters()),
    'instance_norm_rewrite_max_abs':float((actual-reference).abs().max()),
    'scope':'three LUT coefficients from one 256x256 game screenshot, not HDR synthesis or live filtering'}
(ROOT/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
