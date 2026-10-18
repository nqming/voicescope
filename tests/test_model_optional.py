"""Adapter/interface tests only; fake backbone is never a deployable checkpoint."""
import numpy as np
import pytest

torch=pytest.importorskip('torch',reason='PyTorch optional; no DINOv3 weights downloaded')
from voicescope.config import Config
from voicescope.model import Detector,spectrogram_tensor


def test_image_adapter():
    image,mapping=spectrogram_tensor(np.zeros(16000,dtype=np.float32),Config())
    assert image.shape==(3,256,256)
    assert torch.isfinite(image).all()
    assert mapping['hop_seconds']==.01


def test_backbone_contract_freeze_and_gradient(tmp_path,monkeypatch):
    (tmp_path/'hubconf.py').write_text('# test double only')
    class Backbone(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.layer=torch.nn.Linear(3,384)
        def forward(self,x): return self.layer(x.mean(dim=(2,3)))
    monkeypatch.setattr(torch.hub,'load',lambda *a,**k:Backbone())
    cfg=Config(dinov3_repo=str(tmp_path))
    model=Detector(cfg,load_pretrained=False).train()
    assert not model.backbone.training
    logits=model(torch.zeros(2,3,256,256)); logits.sum().backward()
    assert model.head.weight.grad is not None
    assert all(p.grad is None for p in model.backbone.parameters())
    with pytest.raises(ValueError): model(torch.zeros(2,16000))
