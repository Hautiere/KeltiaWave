import { Injectable } from '@angular/core';
import { HttpClient, HttpEventType } from '@angular/common/http';
import { firstValueFrom, timeout, filter, map, tap } from 'rxjs';

export type LiveLanguage = 'br' | 'cy';
export interface LiveCapabilities {
  languages: { br: { live: boolean; whisper: boolean }; cy?: { live:boolean; whisper:boolean; engine?:string; block_seconds?:number } };
  max_session_seconds: number;
  max_audio_upload_bytes: number;
}
export interface LiveEvent { type: 'ready' | 'partial' | 'final' | 'done' | 'error' | 'pong' | 'archive'; text?: string; message?: string; }

@Injectable({ providedIn: 'root' })
export class LiveAudioService {
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private node: AudioWorkletNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private socket: WebSocket | null = null;
  private timer: number | null = null;
  private handshakeTimer: number | null = null;
  private heartbeat: number | null = null;
  private flushed: (() => void) | null = null;
  private active = false;
  private finishing = false;
  private cancelled = false;
  private paused = false;
  private stopWaiter: (() => void) | null = null;
  private generation = 0;
  private recorder: MediaRecorder | null = null;
  private archivedAudio: File | null = null;
  private archiveLanguage:LiveLanguage='br';
  private archiveMessage = '';
  private archiveLimit = 64 * 1024 * 1024;
  private onEvent: (event: LiveEvent) => void = () => {};
  private onEnd: () => void = () => {};

  constructor(private readonly http: HttpClient) {}
  get supported(): boolean { return window.isSecureContext && !!navigator.mediaDevices?.getDisplayMedia && !!window.AudioWorkletNode; }
  get whisperAudio(): File | null { return this.archivedAudio; }
  get whisperAudioMessage(): string { return this.archiveMessage; }
  async capabilities(): Promise<LiveCapabilities> {
    const capabilities = await firstValueFrom(this.http.get<LiveCapabilities>('/api/live/capabilities').pipe(timeout(10000)));
    const limit = capabilities.max_audio_upload_bytes;
    this.archiveLimit = Number.isFinite(limit) && limit > 0 ? Math.min(64 * 1024 * 1024, limit) : 64 * 1024 * 1024;
    return capabilities;
  }
  async whisperEstimate(duration: number): Promise<number> {
    if (duration <= 0) return 0;
    const params = new URLSearchParams({ lang: this.archiveLanguage, mode: 'quality', duration_seconds: String(duration) });
    try {
      const result = await firstValueFrom(this.http.get<{ estimated_seconds: number }>(`/api/transcribe/estimate?${params}`).pipe(timeout(10000)));
      return Number.isFinite(result.estimated_seconds) && result.estimated_seconds > 0 ? result.estimated_seconds : 0;
    } catch { return 0; }
  }
  improve(onUpload: (progress: number | null) => void = () => {}): Promise<{ text: string }> {
    if (!this.archivedAudio) return Promise.reject(new Error('L’audio de cette écoute n’est pas disponible.'));
    const form = new FormData();
    form.append('audio_file', this.archivedAudio, this.archivedAudio.name);
    form.append('language',this.archiveLanguage);
    return firstValueFrom(this.http.post<{ text: string }>(`/api/live/improve`, form, { observe: 'events', reportProgress: true }).pipe(
      tap(event => {
        if (event.type === HttpEventType.UploadProgress) onUpload(event.total ? Math.round(event.loaded * 100 / event.total) : null);
      }),
      filter(event => event.type === HttpEventType.Response),
      map(event => {
        if (!event.body) throw new Error('Réponse Whisper vide.');
        return event.body;
      }),
      timeout(15 * 60 * 1000),
    ));
  }

  async start(onEvent: (event: LiveEvent) => void, onLevel: (level: number) => void, onEnd: () => void, language:LiveLanguage = 'br'): Promise<void> {
    const generation = ++this.generation;
    this.cancelled = false;
    this.finishing = false;
    this.paused = false;
    this.onEvent = onEvent;
    this.onEnd = onEnd;
    try {
      // Must run directly from the user's click, before awaiting network requests.
      // Ask the browser to offer system audio when supported. Source selection
      // and consent remain controlled by the browser, even for system capture.
      const options: DisplayMediaStreamOptions & { systemAudio: 'include' } = {
        video: { displaySurface: 'monitor' }, audio: true, systemAudio: 'include',
      };
      const stream = await navigator.mediaDevices.getDisplayMedia(options);
      if (this.cancelled || generation !== this.generation) { stream.getTracks().forEach(track => track.stop()); return; }
      this.stream = stream;
      if (!stream.getAudioTracks().length) throw new Error('Aucun son partagé. Activez le partage audio dans le sélecteur. Si le son système n’est pas proposé, choisissez l’onglet du podcast avec son audio.');
      stream.getTracks().forEach(track => track.addEventListener('ended', () => { void this.stop(); }, { once: true }));
      // Keep the video track alive for the browser sharing session, but never read or send video.
      const context = new AudioContext();
      this.context = context;
      await context.resume();
      await context.audioWorklet.addModule('/live-pcm-worklet.js');
      if (this.cancelled || this.finishing || generation !== this.generation) return;
      this.source = context.createMediaStreamSource(new MediaStream(stream.getAudioTracks()));
      this.node = new AudioWorkletNode(context, 'live-pcm');
      this.source.connect(this.node);
      this.node.connect(context.destination);
      const url = new URL(location.origin);
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      url.pathname = '/api/live/stream';
      const socket = new WebSocket(url);
      this.socket = socket;
      this.node.port.onmessage = ({ data }: MessageEvent<{ pcm?: ArrayBuffer; level: number; flushed?: boolean }>) => {
        if (data.flushed) { this.flushed?.(); return; }
        if (!this.active || this.paused || socket.readyState !== WebSocket.OPEN) return;
        if (socket.bufferedAmount > 256000) { this.fail('Connexion trop lente : écoute arrêtée pour éviter une transcription décalée.'); return; }
        if (data.pcm) socket.send(data.pcm);
        onLevel(data.level);
      };
      await new Promise<void>((resolve, reject) => {
        let ready = false;
        this.stopWaiter = () => reject(new Error('Démarrage interrompu.'));
        this.handshakeTimer = window.setTimeout(() => { reject(new Error('Le serveur Live ne répond pas.')); }, language === 'cy' ? 30000 : 15000);
        socket.onopen = () => socket.send(JSON.stringify({ type: 'start', language, sample_rate: context.sampleRate }));
        socket.onmessage = ({ data }) => {
          let event: LiveEvent;
          try { event = JSON.parse(String(data)) as LiveEvent; }
          catch { this.fail('Réponse Live invalide.'); return; }
          if (event.type === 'ready') {
            ready = true;
            this.clearHandshake();
            this.stopWaiter = null;
            this.active = true;
            this.startArchive(stream, generation, language);
            this.node?.port.postMessage('resume');
            this.timer = window.setTimeout(() => { void this.stop(); }, 3600000);
            this.heartbeat = window.setInterval(() => {
              if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'ping' }));
            }, 30000);
            resolve();
          } else if (event.type === 'error') {
            if (!ready) reject(new Error(event.message));
            else this.fail(event.message || 'Live est indisponible.');
          } else {
            this.onEvent(event);
            if (event.type === 'done') this.dispose();
          }
        };
        socket.onerror = () => {
          if (!ready) reject(new Error('Connexion au serveur Live impossible.'));
          else this.fail('Connexion interrompue. Le texte déjà reçu est conservé.');
        };
        socket.onclose = () => {
          if (!ready) reject(new Error('Le serveur Live a fermé la connexion.'));
          else if (!this.finishing) this.fail('Connexion interrompue. Le texte déjà reçu est conservé.');
          else this.dispose();
        };
      });
    } catch (error) {
      if (generation === this.generation) this.dispose();
      throw error;
    }
  }

  pause(value: boolean): void {
    this.paused = value;
    if (value && this.recorder?.state === 'recording') this.recorder.pause();
    if (!value && this.recorder?.state === 'paused') this.recorder.resume();
    this.node?.port.postMessage(value ? 'pause' : 'resume');
  }
  async stop(): Promise<void> {
    if (this.finishing) return;
    this.finishing = true;
    this.cancelled = true;
    if (this.timer !== null) window.clearTimeout(this.timer);
    this.timer = null;
    if (!this.active || this.socket?.readyState !== WebSocket.OPEN) { ++this.generation; this.dispose(); return; }
    // Flush the worklet's final short block before sending stop to the backend.
    await new Promise<void>(resolve => {
      const node = this.node;
      if (!node) { resolve(); return; }
      const finish = (): void => { this.flushed = null; resolve(); };
      this.flushed = finish;
      node.port.postMessage('flush');
      window.setTimeout(() => { if (this.flushed === finish) finish(); }, 500);
    });
    if (this.socket?.readyState !== WebSocket.OPEN) return;
    this.active = false;
    this.releaseCapture();
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: 'stop' }));
    this.timer = window.setTimeout(() => { this.fail('La finalisation a expiré. Le texte déjà reçu est conservé.'); }, this.archiveLanguage === 'cy' ? 60000 : 10000);
  }
  destroy(): void { ++this.generation; this.cancelled = true; this.finishing = true; this.dispose(); this.archivedAudio = null; }
  private fail(message: string): void {
    this.onEvent({ type: 'error', message });
    this.finishing = true;
    this.dispose();
  }
  private clearHandshake(): void {
    if (this.handshakeTimer !== null) window.clearTimeout(this.handshakeTimer);
    this.handshakeTimer = null;
  }
  private releaseCapture(): void {
    if (this.recorder && this.recorder.state !== 'inactive') this.recorder.stop();
    this.recorder = null;
    this.stream?.getTracks().forEach(track => track.stop()); this.stream = null;
    this.node?.disconnect(); this.node = null;
    this.source?.disconnect(); this.source = null;
    void this.context?.close().catch(() => {}); this.context = null;
  }
  private startArchive(stream: MediaStream, generation: number, language:LiveLanguage): void {
    this.archiveLanguage=language;
    this.archivedAudio = null;
    this.archiveMessage = '';
    const mime = typeof MediaRecorder !== 'undefined' && ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']
      .find(type => MediaRecorder.isTypeSupported(type));
    if (!mime) { this.archiveMessage = 'Ce navigateur ne permet pas de conserver l’audio pour Whisper.'; return; }
    try {
      const recorder = new MediaRecorder(new MediaStream(stream.getAudioTracks()), { mimeType: mime, audioBitsPerSecond: 64000 });
      this.recorder = recorder;
      const chunks: Blob[] = [];
      let size = 0;
      let valid = true;
      recorder.ondataavailable = ({ data }) => {
        if (!valid || generation !== this.generation) return;
        size += data.size;
        if (size > this.archiveLimit) {
          valid = false; chunks.length = 0;
          this.archiveMessage = 'L’audio dépasse la limite de taille pour Whisper. La transcription Vosk reste disponible.';
          if (recorder.state !== 'inactive') recorder.stop();
          return;
        }
        if (data.size) chunks.push(data);
      };
      recorder.onerror = () => {
        if (generation !== this.generation) return;
        valid = false; chunks.length = 0;
        this.archiveMessage = 'L’audio n’a pas pu être conservé pour Whisper. Le texte Vosk reste disponible.';
        this.onEvent({ type: 'archive' });
      };
      recorder.onstop = () => {
        if (generation !== this.generation) return;
        if (valid && size > 0) {
          const extension = mime.includes('mp4') ? 'm4a' : mime.includes('ogg') ? 'ogg' : 'webm';
          this.archivedAudio = new File(chunks, `keltiawave-live.${extension}`, { type: mime });
        } else if (valid) {
          this.archiveMessage = 'Aucun audio n’a été conservé pour Whisper. Vous pouvez démarrer une nouvelle écoute.';
        }
        chunks.length = 0;
        this.onEvent({ type: 'archive' });
      };
      recorder.start(1000);
    } catch {
      this.recorder = null;
      this.archiveMessage = 'L’audio n’a pas pu être conservé pour Whisper. Le texte Vosk reste disponible.';
    }
  }
  private dispose(): void {
    this.active = false;
    this.clearHandshake();
    this.flushed?.(); this.flushed = null;
    if (this.heartbeat !== null) window.clearInterval(this.heartbeat); this.heartbeat = null;
    this.stopWaiter?.(); this.stopWaiter = null;
    if (this.timer !== null) window.clearTimeout(this.timer); this.timer = null;
    this.releaseCapture();
    if (this.socket) {
      this.socket.onclose = null; this.socket.onerror = null; this.socket.onmessage = null;
      this.socket.close(); this.socket = null;
    }
    this.onEnd();
  }
}
