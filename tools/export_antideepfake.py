"""Build a Q4 deployment copy of the pinned NII research checkpoint.
Original weights: NII Yamagishi Lab, CC BY-NC-SA 4.0. No training or user audio.
"""
import json,re
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file
from transformers import Wav2Vec2Config,Wav2Vec2Model

torch.set_num_threads(1)
class Detector(torch.nn.Module):
    def __init__(self, source):
        super().__init__()
        cfg=Wav2Vec2Config.from_json_file(str(source/'config.json'))
        cfg._attn_implementation='eager'
        self.wav2vec2=Wav2Vec2Model(cfg)
        self.proj_fc=torch.nn.Linear(768,2)
    def forward(self,x):
        return self.proj_fc(self.wav2vec2(x).last_hidden_state.mean(dim=1))

def load_model(source):
    model=Detector(source)
    source=load_file(str(source/'model.safetensors'))
    mapped={}; skipped=[]
    for key,value in source.items():
        if key.startswith('proj_fc.'):
            mapped[key]=value;continue
        k=key.removeprefix('m_ssl.model.')
        if k.startswith(('quantizer.','project_q.','final_proj.')):
            skipped.append(key);continue  # training-only contrastive heads
        k=re.sub(r'feature_extractor.conv_layers.(\d+).0.',r'feature_extractor.conv_layers.\1.conv.',k)
        k=k.replace('feature_extractor.conv_layers.0.2.','feature_extractor.conv_layers.0.layer_norm.')
        k=k.replace('post_extract_proj.','feature_projection.projection.')
        if k.startswith('layer_norm.'): k='feature_projection.'+k
        k=k.replace('encoder.pos_conv.0.weight_g','encoder.pos_conv_embed.conv.parametrizations.weight.original0')
        k=k.replace('encoder.pos_conv.0.weight_v','encoder.pos_conv_embed.conv.parametrizations.weight.original1')
        k=k.replace('encoder.pos_conv.0.bias','encoder.pos_conv_embed.conv.bias')
        k=k.replace('.self_attn.','.attention.').replace('.self_attn_layer_norm.','.layer_norm.')
        k=k.replace('.fc1.','.feed_forward.intermediate_dense.').replace('.fc2.','.feed_forward.output_dense.')
        if k=='mask_emb':k='masked_spec_embed'
        mapped['wav2vec2.'+k]=value
    model.load_state_dict(mapped,strict=True)
    print('Strict state_dict loaded; omitted only training heads:',len(skipped),flush=True)
    return model.eval()

if __name__ == '__main__':
    import argparse,hashlib,urllib.request,logging
    from onnxruntime.quantization.matmul_4bits_quantizer import MatMul4BitsQuantizer
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fetch',action='store_true')
    args=parser.parse_args()
    revision='9a13264b5dcc827a8d5a4f8e01fccefa392f886b'
    repo='nii-yamagishilab/wav2vec-small-anti-deepfake'
    hashes={'config.json':'0fa206bdf51cd69834414610ba6df68a1f22fe0397fe6a6826017b3d406fb69f',
            'model.safetensors':'828ee456122f86d5d631cb7895a10e5c62c78a4fcb8a8b1c42cb5838a9abcfe0'}
    args.source.mkdir(parents=True,exist_ok=True);args.output.mkdir(parents=True,exist_ok=True)
    def sha(path):
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        return h.hexdigest()
    for name in [*hashes,'README.md']:
        path=args.source/name
        if args.fetch: urllib.request.urlretrieve(f'https://huggingface.co/{repo}/resolve/{revision}/{name}',path)
        if name in hashes and sha(path)!=hashes[name]:raise ValueError('Source checksum mismatch: '+name)
    torch.manual_seed(42)
    model=load_model(args.source)
    # Export uses public weights and a synthetic tensor only. No microphone data.
    sample=torch.zeros(1,64600)
    fp=args.source/'model.onnx';quant=args.output/'model_q4.onnx'
    torch.onnx.export(model,(sample,),str(fp),input_names=['input_values'],output_names=['logits'],
                      dynamic_axes={'input_values':{0:'batch',1:'samples'},'logits':{0:'batch'}},
                      opset_version=17,dynamo=False)
    logging.getLogger('onnxruntime.quantization.matmul_4bits_quantizer').setLevel(logging.ERROR)
    quantizer=MatMul4BitsQuantizer(str(fp),block_size=32,is_symmetric=True,accuracy_level=1)
    quantizer.process()
    quantizer.model.save_model_to_file(str(quant),use_external_data_format=False)
    manifest={'model':'NII AntiDeepfake Wav2Vec2-Small Q4','upstream':repo,'revision':revision,
              'source_sha256':hashes['model.safetensors'],'sha256':sha(quant),
              'labels':['fake','real'],'normalize_epsilon':1e-5,
              'license':'CC-BY-NC-SA-4.0','license_url':'https://creativecommons.org/licenses/by-nc-sa/4.0/',
              'modification':'Fairseq state mapping to Transformers; ONNX export; 4-bit MatMul weights, FP32 activation compute; no retraining'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (args.output/'model-card.md').write_bytes((args.source/'README.md').read_bytes())
    print(json.dumps(manifest),flush=True)

