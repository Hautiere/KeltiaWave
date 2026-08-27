// frontend/src/app/core/audio-recorder.service.ts
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AudioRecorderService {
  private mediaRecorder?: MediaRecorder;
  private chunks: BlobPart[] = [];
  private stream?: MediaStream;
  private chosenMime = '';

  /** MIME actually used, when known. */
  get mimeType(): string {
    return this.mediaRecorder?.mimeType || this.chosenMime || '';
  }

  /** Is recording currently active? */
  get isRecording(): boolean {
    return !!this.mediaRecorder && this.mediaRecorder.state === 'recording';
  }

  /** Selects a supported MIME type in preference order. */
  private pickMime(): string {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
      'audio/mp4', // Safari/iOS
    ];
    for (const c of candidates) {
      if ((window as any).MediaRecorder?.isTypeSupported?.(c)) return c;
    }
    return ''; // Let the browser decide.
  }

  /** Requests microphone access. */
  async init(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Your browser does not support audio recording.');
    }
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  }

  /** Starts recording. */
  start(timesliceMs: number = 1000): void {
    if (!this.stream) throw new Error('Microphone not initialized. Call init() before start().');
    if (this.isRecording) return; // Already recording.

    this.chunks = [];
    this.chosenMime = this.pickMime();

    this.mediaRecorder = new MediaRecorder(
      this.stream,
      this.chosenMime ? { mimeType: this.chosenMime } : undefined
    );

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size) this.chunks.push(e.data);
    };

    this.mediaRecorder.start(timesliceMs); // Chunks every second.
  }

  /** Stops recording and returns the Blob with the selected type. */
  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      const mr = this.mediaRecorder;
      if (!mr) return reject(new Error('No recording in progress.'));

      mr.onstop = () => {
        const type =
          mr.mimeType ||
          (this.chunks.length ? (this.chunks[0] as any).type : '') ||
          'audio/webm';

        const blob = new Blob(this.chunks, { type });

        // Release the microphone.
        this.stream?.getTracks().forEach((t) => t.stop());
        this.stream = undefined;
        this.mediaRecorder = undefined;
        this.chunks = [];

        resolve(blob);
      };

      try { mr.requestData?.(); } catch {}
      mr.stop();
    });
  }

  /** Stops everything cleanly without returning a blob. */
  dispose(): void {
    try { this.mediaRecorder?.stop(); } catch {}
    this.mediaRecorder?.stream?.getTracks().forEach((t) => t.stop());
    this.stream?.getTracks().forEach((t) => t.stop());
    this.mediaRecorder = undefined;
    this.stream = undefined;
    this.chunks = [];
  }
}
