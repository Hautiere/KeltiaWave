import { Injectable } from '@angular/core';

// Capture PCM directly so the browser can replay exactly the file we upload.
@Injectable({ providedIn: 'root' })
export class WavRecorderService {
  private stream?: MediaStream;
  private context?: AudioContext;
  private source?: MediaStreamAudioSourceNode;
  private processor?: ScriptProcessorNode;
  private chunks: Float32Array[] = [];
  private sampleCount = 0;
  private active = false;

  get isRecording(): boolean {
    return this.active;
  }

  async init(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('Microphone unavailable');
    this.dispose();
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
    this.context = new AudioContext();
    await this.context.resume();
  }

  start(): void {
    if (!this.stream || !this.context) throw new Error('Microphone not initialized');
    if (this.active) return;
    this.chunks = [];
    this.sampleCount = 0;
    this.source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (event) => {
      if (!this.active) return;
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      this.chunks.push(samples);
      this.sampleCount += samples.length;
      event.outputBuffer.getChannelData(0).fill(0);
    };
    this.source.connect(this.processor);
    this.processor.connect(this.context.destination);
    this.active = true;
  }

  async stop(): Promise<Blob> {
    if (!this.active || !this.context) throw new Error('No recording in progress');
    const sampleRate = this.context.sampleRate;
    this.active = false;
    this.disconnect();
    const blob = this.encodeWav(sampleRate);
    this.closeResources();
    if (this.sampleCount === 0) throw new Error('No audio samples recorded');
    return blob;
  }

  dispose(): void {
    this.active = false;
    this.disconnect();
    this.closeResources();
    this.chunks = [];
    this.sampleCount = 0;
  }

  private disconnect(): void {
    if (this.processor) {
      this.processor.onaudioprocess = null;
      this.processor.disconnect();
      this.processor = undefined;
    }
    this.source?.disconnect();
    this.source = undefined;
  }

  private closeResources(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = undefined;
    if (this.context) void this.context.close();
    this.context = undefined;
  }

  private encodeWav(sampleRate: number): Blob {
    const buffer = new ArrayBuffer(44 + this.sampleCount * 2);
    const view = new DataView(buffer);
    const write = (offset: number, value: string) => {
      for (let i = 0; i < value.length; i += 1) view.setUint8(offset + i, value.charCodeAt(i));
    };
    write(0, 'RIFF');
    view.setUint32(4, 36 + this.sampleCount * 2, true);
    write(8, 'WAVE');
    write(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    write(36, 'data');
    view.setUint32(40, this.sampleCount * 2, true);
    let offset = 44;
    for (const chunk of this.chunks) {
      for (const sample of chunk) {
        const value = Math.max(-1, Math.min(1, sample));
        view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true);
        offset += 2;
      }
    }
    return new Blob([buffer], { type: 'audio/wav' });
  }
}
