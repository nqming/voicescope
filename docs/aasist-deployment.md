# AASIST-L production model
Upstream: https://github.com/clovaai/aasist
Revision: a04c9863f63d44471dde8a6abcb3b082b07cd1d1
Official architecture and checkpoint AASIST-L. MIT license and NOTICE preserved in voicescope/aasist_license.py.
SHA256: 814331d088032bb4c3fa61cc014789eadeed464209dd094ab3a2dd6ffbdce27a
85,306 parameters. Training corpus: ASVspoof 2019 LA. Vietnamese accuracy has not been evaluated.
Docker downloads pinned checkpoint at build and checks hash; CPU PyTorch 2.7.1.
VOICESCOPE_MODEL=aasist-l selects this service; VOICESCOPE_AASIST_WEIGHTS overrides checkpoint path.
Preprocessing: existing decoder, mono 16 kHz, contiguous 64600-sample windows, repeat padding matching official evaluation. Class 0 spoof, 1 bonafide. Duration-weighted mean of softmax spoof scores, fixed threshold 0.5. Scores are uncalibrated.

Production verification 2026-10-30:
- Render deployed 04857f7; /health model_ready true; /ready HTTP 200.
- Sent two ASVspoof dev clips (one bonafide, one spoof) to live /inference.
- Bonafide: real, fake_score 0.00017197485. Spoof: fake, fake_score 0.99997162819.
- Evidence: artifacts/aasist-render-smoke.json and artifacts/aasist-production-inference.json.
- These two integration examples do not measure overall model accuracy or Vietnamese generalization.
- Commit 3fd2b8a adds bounded health reconnect and model identity to health response.

Browser readiness fix: the installed browser client blocked /health subrequests with ERR_BLOCKED_BY_CLIENT. Application now uses /api/status (same response, no-store); /health remains for Render and CLI. Commit 027fded deploys this fix.

Final Render version 027fded: Live. Browser visibly shows Sẵn sàng phân tích and AASIST-L đã nạp. Sẵn sàng phân tích âm thanh.
