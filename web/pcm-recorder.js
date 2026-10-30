// Capture raw microphone PCM without a lossy MediaRecorder codec.
class PCMRecorder extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = new Float32Array(2048);
    this.offset = 0;
    this.stopped = false;
    this.port.onmessage = event => {
      if (event.data === 'stop') {
        this.flush();
        this.stopped = true;
        this.port.postMessage({stopped: true});
      }
    };
  }
  flush() {
    if (!this.offset) return;
    const block = this.samples.slice(0, this.offset);
    this.port.postMessage({samples: block}, [block.buffer]);
    this.offset = 0;
  }
  process(inputs) {
    if (this.stopped) return false;
    const channels = inputs[0];
    if (!channels?.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let value = 0;
      for (const channel of channels) value += channel[i] / channels.length;
      this.samples[this.offset++] = value;
      if (this.offset === this.samples.length) this.flush();
    }
    return true;
  }
}
registerProcessor('pcm-recorder', PCMRecorder);
