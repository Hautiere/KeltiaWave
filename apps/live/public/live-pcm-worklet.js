// Keep audio processing off the UI thread. The output is intentionally silent:
// the original tab already plays the podcast, so monitoring would cause an echo.
class LivePcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.enabled = false;
    this.buffer = new Int16Array(2048);
    this.offset = 0;
    this.peak = 0;
    this.port.onmessage = ({ data }) => {
      if (data === 'flush') {
        this.flush();
        this.port.postMessage({ flushed: true });
      }
      else {
        this.enabled = data === 'resume';
        if (!this.enabled) this.flush();
      }
    };
  }
  flush() {
    if (!this.offset) return;
    const pcm = this.buffer.slice(0, this.offset).buffer;
    this.port.postMessage({ pcm, level: this.peak }, [pcm]);
    this.offset = 0;
    this.peak = 0;
  }
  process(inputs) {
    const channels = inputs[0];
    if (!this.enabled || !channels?.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let sample = 0;
      for (const channel of channels) sample += channel[i] || 0;
      sample = Math.max(-1, Math.min(1, sample / channels.length));
      this.peak = Math.max(this.peak, Math.abs(sample));
      this.buffer[this.offset++] = Math.round(sample * (sample < 0 ? 32768 : 32767));
      if (this.offset === this.buffer.length) this.flush();
    }
    return true;
  }
}
registerProcessor('live-pcm', LivePcmProcessor);
