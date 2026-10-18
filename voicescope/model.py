"""Optional PyTorch dependency; imported only for actual ML operations."""
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F
from .audio import log_mel

BACKBONES={'dinov3_vits16':384,'dinov3_vits16plus':384,'dinov3_vitb16':768,'dinov3_vitl16':1024}
PREPROCESS_VERSION='logmel-htk-periodic-hann-fixed-db-v1'


def spectrogram_tensor(wave,cfg):
    image,times=log_mel(wave,cfg)
    x=torch.from_numpy(image).unsqueeze(0).unsqueeze(0)
    x=F.interpolate(x,size=(cfg.image_size,cfg.image_size),mode='bilinear',align_corners=False,antialias=True)
    x=x.repeat(1,3,1,1)
    mean=x.new_tensor([.485,.456,.406]).view(1,3,1,1)
    std=x.new_tensor([.229,.224,.225]).view(1,3,1,1)
    # Keep full width: no random crop or horizontal flip of time.
    mapping={'frame_centers_seconds':times.tolist(),'source_columns':len(times),
             'image_columns':cfg.image_size,'hop_seconds':cfg.hop_length/cfg.sample_rate,
             'first_center_seconds':cfg.win_length/2/cfg.sample_rate,
             'resize_rule':'source_index=(pixel+0.5)*source_columns/image_columns-0.5; clamp endpoints'}
    return ((x-mean)/std).squeeze(0),mapping


class Detector(nn.Module):
    def __init__(self,cfg,load_pretrained=True):
        super().__init__()
        if cfg.backbone not in BACKBONES:
            raise ValueError('Backbone chưa hỗ trợ: '+cfg.backbone)
        if not cfg.dinov3_repo or not (Path(cfg.dinov3_repo)/'hubconf.py').is_file():
            raise ValueError('Cần clone repository DINOv3 chính thức và cấu hình đường dẫn local.')
        kwargs={'pretrained':False}
        if load_pretrained:
            if not cfg.backbone_weights or not Path(cfg.backbone_weights).is_file():
                raise ValueError('Thiếu DINOv3 weights local đã được cấp quyền.')
            kwargs={'weights':str(Path(cfg.backbone_weights).resolve())}
        self.backbone=torch.hub.load(str(Path(cfg.dinov3_repo).resolve()),cfg.backbone,source='local',**kwargs)
        self.head=nn.Linear(BACKBONES[cfg.backbone],2)
        self.frozen=cfg.freeze_backbone
        self.backbone.requires_grad_(not self.frozen)

    def train(self,mode=True):
        super().train(mode)
        if self.frozen:
            self.backbone.eval()
        return self

    def forward(self,x):
        if x.ndim!=4 or x.shape[1]!=3:
            raise ValueError('DINOv3 chỉ nhận ảnh phổ [B,3,H,W], không nhận waveform.')
        if self.frozen:
            with torch.no_grad():
                embedding=self.backbone(x)
        else:
            embedding=self.backbone(x)
        return self.head(embedding)
