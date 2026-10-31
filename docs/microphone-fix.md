# Microphone false-positive investigation — 2026-10-30

Production originally used AASIST-L trained on ASVspoof 2019 LA. The supplied genuine microphone clip was classified fake (0.8323). On a diagnostic sample of 12 genuine Vietnam-Celeb clips, AASIST-L rejected all 12. This reproduces a cross-domain failure, not a label inversion.

A comparison candidate that classified the microphone real but missed all eight ASVspoof spoof examples was rejected.

Replacement: NII Yamagishi Lab wav2vec-small-anti-deepfake, revision 9a13264b5dcc827a8d5a4f8e01fccefa392f886b. Official model card: https://huggingface.co/nii-yamagishilab/wav2vec-small-anti-deepfake
The model weights are CC BY-NC-SA 4.0 (research/education, noncommercial). Attribution and license links are shown in the web footer. Original model card and conversion manifest are retained in the deployment image. No retraining or threshold tuning on the user clip.

Conversion uses strict state_dict mapping from Fairseq to Transformers Wav2Vec2, discards only the seven training-only contrastive-head tensors, mean pooling and original FC classifier. Original preprocessing layer_norm epsilon 1e-5 is preserved. Export uses synthetic zeros only; no user audio is included in code, weights, image or network requests. ONNX Q4 weight-only MatMul quantization with FP32 activation compute runs during Docker build; production runs ONNX Runtime CPU without PyTorch.

## Local checks (diagnostic samples, not a full benchmark)

| Group | Result |
|---|---|
| Supplied genuine microphone clip | real, fake_score 0.2832 |
| Same clip at -12 dB and +6 dB, with 0.25 s and 1 s silence at both ends | all four variants real |
| 12 genuine Vietnam-Celeb clips | 12 real |
| 8 genuine ASVspoof dev clips | 8 real |
| 8 spoof ASVspoof dev clips | 7 fake, 1 missed |

Sample selection and candidate comparison are development checks; they must not be presented as an unbiased estimate of generalization. Additional unseen microphone speakers/devices and spoof sources are required before claiming deployment accuracy. A correct result on one supplied clip cannot guarantee correctness on every future recording.

## Recording changes

AudioWorklet captures mono PCM directly; MediaRecorder/codec round-trip removed. Existing WAV encoder exports PCM16 at capture sample rate; server resamples to 16 kHz. Capture is bounded by duration and file-size limits. Network upload still occurs only when the user requests analysis. Unit verification: `node tests/test_pcm_capture.cjs` checks stereo downmix, exact sample count/order, final partial block, stop signal and WAV sample-rate/quantization.

## TF-C

Neither the old AASIST-L nor the deployed AntiDeepfake checkpoint implements the TF-C objective. Wav2Vec2 self-supervision is not TF-C. The project includes TF-C as a literature reference, not as a reproduced component. TF-C source: https://github.com/mims-harvard/TFC-pretraining

Private audio and individual diagnostic reports remain local under ignored data/ and artifacts/.

## Cross-CPU deployment check
The initial INT8 candidate was rejected after live Render inference disagreed with local inference on an ASVspoof spoof sample. A passing local model-readiness check alone was insufficient. The revised export stores Q4 weights and explicitly selects FP32 activation compute (accuracy_level=1), with only basic runtime graph optimization. No label override or threshold adjustment is used. Evidence files: artifacts/user-mic-q4-final.json, artifacts/antideepfake-q4-fp-comparison.json. The user recording has not been uploaded to production.

## Final production verification
Render commit a9038bc210cbb29fa8a681bc16186b179ee236fa is Live with model NII AntiDeepfake Wav2Vec2-Small Q4. Status reports model_ready true; the PCM worklet resource is served. Two public ASVspoof real clips returned real; two public spoof clips returned fake. Scores agree with local Q4 reference (for example spoof LA_D_2118489: 0.999976 on both systems). Report: artifacts/antideepfake-q4-production-verification.json. This replaces the rejected INT8 deployment. The supplied user microphone clip was evaluated only locally and was not uploaded.
