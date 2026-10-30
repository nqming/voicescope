FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    VOICESCOPE_CONFIG=/app/configs/default.json \
    VOICESCOPE_DEVICE=cpu

WORKDIR /app
COPY requirements-runtime.txt ./
RUN python -m pip install --no-cache-dir -r requirements-runtime.txt \
    && useradd --create-home --uid 10001 appuser

# Explicit source allowlist. Never COPY the dataset or weights into an image.
COPY voicescope/ ./voicescope/
COPY web/ ./web/
COPY configs/default.json ./configs/default.json
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=4)"
CMD ["python", "-m", "voicescope.server"]

# Optional CPU inference target. Build only after selecting a DINOv3 revision.
# Full detector checkpoint is mounted at runtime, never added to the image.
FROM runtime AS inference
USER root
ARG DINOV3_REF
RUN python -c "import os,re; assert re.fullmatch('[0-9a-fA-F]{40}', os.environ.get('DINOV3_REF','')), 'DINOV3_REF must be a full commit SHA'" \
    && apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git init /opt/dinov3 \
    && git -C /opt/dinov3 remote add origin https://github.com/facebookresearch/dinov3.git \
    && git -C /opt/dinov3 fetch --depth 1 origin "$DINOV3_REF" \
    && git -C /opt/dinov3 checkout --detach FETCH_HEAD
RUN python -m pip install --no-cache-dir 'torch==2.7.1' --index-url https://download.pytorch.org/whl/cpu
ENV VOICESCOPE_DINOV3_REPO=/opt/dinov3
USER appuser

# Export the public research checkpoint at build time. No user audio enters this stage.
FROM runtime AS antideepfake-build
USER root
RUN python -m pip install --no-cache-dir 'torch==2.7.1' --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --no-cache-dir 'transformers==4.57.6' 'safetensors==0.8.0' 'onnx==1.23.2' 'onnxruntime==1.20.1'
COPY tools/export_antideepfake.py /build/export_antideepfake.py
RUN python /build/export_antideepfake.py --fetch --source /opt/source --output /opt/export

# Production runs ONNX only; large training libraries stay in the build stage.
FROM runtime AS web
USER root
RUN python -m pip install --no-cache-dir 'onnxruntime==1.20.1'
COPY --from=antideepfake-build /opt/export /opt/models/antideepfake
ENV VOICESCOPE_MODEL=antideepfake-int8
USER appuser
