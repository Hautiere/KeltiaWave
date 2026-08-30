import { CommonModule } from '@angular/common';
import { Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RecordApiService, RecordLanguage } from './record-api.service';

type InterfaceLanguage = 'en' | 'fr' | 'br' | 'cy';
const RECORD_COPY: Record<Exclude<InterfaceLanguage, 'en'>, Record<string, string>> = {
  fr: {'Tools for Brittonic languages':'Outils pour les langues brittoniques','Other tools':'Autres outils','Record your voice and get real-time transcription.':'Enregistrez votre voix et obtenez une transcription en temps réel.','Language':'Langue','Breton':'Breton','Welsh':'Gallois','Mode':'Mode','Live + Quality':'Direct + Qualité','Whisper quality':'Qualité Whisper','Tip':'Conseil','Speak clearly, at a steady pace':'Parlez clairement, à un rythme régulier','Recording in progress':'Enregistrement en cours','Recording ready':'Enregistrement prêt','Ready to record':'Prêt à enregistrer','Stop recording':'Arrêter l’enregistrement','Start recording':'Démarrer l’enregistrement','Tap to stop':'Cliquez pour arrêter','Tap to record again':'Cliquez pour recommencer','Click the microphone to start':'Cliquez sur le microphone pour commencer','Transcription versions':'Versions de transcription','Transcription (real-time)':'Transcription en temps réel','Live':'Direct','versions':'versions','Ready':'Prêt','Your transcription will appear here while you speak…':'Votre transcription apparaîtra ici pendant que vous parlez…','Record first, then generate the Welsh transcription with Whisper…':'Enregistrez d’abord, puis générez la transcription galloise avec Whisper…','Live draft':'Brouillon en direct','High accuracy':'Haute précision','words':'mots','characters':'caractères','Words':'Mots','Characters':'Caractères','Vosk and Whisper are both kept and editable':'Les versions Vosk et Whisper sont conservées et modifiables','Recording settings':'Paramètres d’enregistrement','Microphone':'Microphone','Default microphone':'Microphone par défaut','Clear recording':'Effacer l’enregistrement','is available after recording to improve the Vosk draft.':'est disponible après l’enregistrement pour améliorer le brouillon Vosk.','Processing…':'Traitement…','Download audio':'Télécharger l’audio','Download text':'Télécharger le texte','Save Vosk':'Enregistrer Vosk','Save Whisper':'Enregistrer Whisper','Save both':'Enregistrer les deux'},
  br: {'Tools for Brittonic languages':'Ostilhoù evit ar yezhoù predenek','Other tools':'Ostilhoù all','Record your voice and get real-time transcription.':'Enrollit ho mouezh hag obtenit un treuzskrivadur war-eeun.','Language':'Yezh','Breton':'Brezhoneg','Welsh':'Kembraeg','Mode':'Mod','Live + Quality':'War-eeun + Kalite','Whisper quality':'Kalite Whisper','Tip':'Ali','Speak clearly, at a steady pace':'Komzit sklaer, gant ul lusk reizh','Recording in progress':'O enrollañ','Recording ready':'Enrolladenn prest','Ready to record':'Prest da enrollañ','Stop recording':'Paouez da enrollañ','Start recording':'Kregiñ da enrollañ','Tap to stop':'Klikit evit paouez','Tap to record again':'Klikit evit enrollañ en-dro','Click the microphone to start':'Klikit war ar mikrofon evit kregiñ','Transcription versions':'Stummoù an treuzskrivadur','Transcription (real-time)':'Treuzskrivadur war-eeun','Live':'War-eeun','versions':'stumm','Ready':'Prest','Your transcription will appear here while you speak…':'Amañ e vo diskouezet ho treuzskrivadur…','Live draft':'Brouilhed war-eeun','High accuracy':'Resisted uhel','words':'ger','characters':'arouezenn','Words':'Gerioù','Characters':'Arouezennoù','Recording settings':'Arventennoù enrollañ','Microphone':'Mikrofon','Default microphone':'Mikrofon dre ziouer','Clear recording':'Diverkañ an enrolladenn','Processing…':'O tretiñ…','Download audio':'Pellgargañ an audio','Download text':'Pellgargañ an destenn','Save Vosk':'Enrollañ Vosk','Save Whisper':'Enrollañ Whisper','Save both':'Enrollañ an daou'},
  cy: {'Tools for Brittonic languages':'Offer ar gyfer ieithoedd Brythonaidd','Other tools':'Offer eraill','Record your voice and get real-time transcription.':'Recordiwch eich llais a chael trawsgrifiad byw.','Language':'Iaith','Breton':'Llydaweg','Welsh':'Cymraeg','Mode':'Modd','Live + Quality':'Byw + Ansawdd','Whisper quality':'Ansawdd Whisper','Tip':'Awgrym','Speak clearly, at a steady pace':'Siaradwch yn glir ac yn gyson','Recording in progress':'Wrthi’n recordio','Recording ready':'Recordiad yn barod','Ready to record':'Barod i recordio','Stop recording':'Stopio recordio','Start recording':'Dechrau recordio','Tap to stop':'Cliciwch i stopio','Tap to record again':'Cliciwch i recordio eto','Click the microphone to start':'Cliciwch y meicroffon i ddechrau','Transcription versions':'Fersiynau trawsgrifio','Transcription (real-time)':'Trawsgrifiad byw','Live':'Byw','versions':'fersiwn','Ready':'Barod','Your transcription will appear here while you speak…':'Bydd eich trawsgrifiad yn ymddangos yma…','Live draft':'Drafft byw','High accuracy':'Cywirdeb uchel','words':'gair','characters':'nod','Words':'Geiriau','Characters':'Nodau','Recording settings':'Gosodiadau recordio','Microphone':'Meicroffon','Default microphone':'Meicroffon diofyn','Clear recording':'Clirio’r recordiad','Processing…':'Wrthi’n prosesu…','Download audio':'Lawrlwytho sain','Download text':'Lawrlwytho testun','Save Vosk':'Cadw Vosk','Save Whisper':'Cadw Whisper','Save both':'Cadw’r ddau'}
};

@Component({ selector: 'record-root', standalone: true, imports: [CommonModule, FormsModule], templateUrl: './record-app.component.html', styleUrls: ['./record-app.component.scss', './keltia-footer.scss'] })
export class RecordAppComponent implements OnInit, OnDestroy {
  readonly portalUrl = window.location.hostname.endsWith('.staging.keltiawave.com')
    ? 'https://staging.keltiawave.com/'
    : 'https://keltiawave.com/';
  interfaceLanguage: InterfaceLanguage = this.initialInterfaceLanguage();
  language: RecordLanguage = 'br';
  microphones: MediaDeviceInfo[] = [];
  microphoneId = '';
  recording = false;
  busy = false;
  whisperProgress = 0;
  live = false;
  elapsed = '00:00';
  draft = '';
  improved = '';
  showDraft = false;
  message = 'Autorisez le microphone pour commencer.';
  error = '';
  audioUrl = '';
  audioFile: File | null = null;
  readonly bars = Array.from({ length: 42 }, (_, index) => 12 + ((index * 17) % 34));

  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private timer: number | null = null;
  private startedAt = 0;
  private socket: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private committed = '';
  private partial = '';
  private whisperProgressTimer: number | null = null;

  constructor(readonly api: RecordApiService, private readonly zone: NgZone) {}

  t(source: string): string {
    const special: Record<string, Record<InterfaceLanguage, string>> = {
      'Generate text with Whisper': { en:'Generate text with Whisper', fr:'Générer le texte avec Whisper', br:'Krouiñ an destenn gant Whisper', cy:'Creu testun gyda Whisper' },
      'Improve with Whisper': { en:'Improve with Whisper', fr:'Améliorer avec Whisper', br:'Gwellaat gant Whisper', cy:'Gwella gyda Whisper' },
      'Estimated progress — completion is confirmed only when the result is received.': { en:'Estimated progress — completion is confirmed only when the result is received.', fr:'Progression estimée — la fin est confirmée uniquement à la réception du résultat.', br:'Araokadenn priziet — kadarnaet eo an dibenn pa vez resevet an disoc’h hepken.', cy:'Cynnydd amcangyfrifedig — cadarnheir ei fod wedi gorffen pan dderbynnir y canlyniad.' },
    };
    return special[source]?.[this.interfaceLanguage] || (this.interfaceLanguage === 'en' ? source : RECORD_COPY[this.interfaceLanguage][source] || source);
  }
  changeInterfaceLanguage(language: string): void {
    this.interfaceLanguage = language as InterfaceLanguage;
    localStorage.setItem('keltiawave-public-language', this.interfaceLanguage);
    document.documentElement.lang = this.interfaceLanguage;
  }

  async ngOnInit(): Promise<void> { await this.loadMicrophones(); }
  ngOnDestroy(): void { this.cleanup(); if (this.audioUrl) URL.revokeObjectURL(this.audioUrl); }

  get transcript(): string { return this.showDraft || !this.improved ? this.draft : this.improved; }
  set transcript(value: string) { if (this.showDraft || !this.improved) this.draft = value; else this.improved = value; }
  get wordCount(): number { return this.transcript.trim() ? this.transcript.trim().split(/\s+/).length : 0; }
  get characterCount(): number { return this.transcript.length; }
  countWords(value: string): number { return value.trim() ? value.trim().split(/\s+/).length : 0; }
  get canUseWhisper(): boolean { return !!this.audioFile && !this.recording && !this.busy && (this.language === 'cy' || !!this.draft.trim()); }
  get whisperLabel(): string { return this.t(this.language === 'cy' && !this.draft.trim() ? 'Generate text with Whisper' : 'Improve with Whisper'); }

  async toggleRecording(): Promise<void> { this.recording ? this.stopRecording() : await this.startRecording(); }

  async startRecording(): Promise<void> {
    this.error = ''; this.improved = ''; this.draft = ''; this.showDraft = false; this.committed = ''; this.partial = '';
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: this.microphoneId ? { deviceId: { exact: this.microphoneId } } : true });
      const mime = this.pickMime(); this.chunks = [];
      this.recorder = mime ? new MediaRecorder(this.stream, { mimeType: mime }) : new MediaRecorder(this.stream);
      this.recorder.ondataavailable = event => { if (event.data.size) this.chunks.push(event.data); };
      this.recorder.onstop = () => this.zone.run(() => this.finalizeRecording());
      this.recorder.start(); this.recording = true; this.startedAt = Date.now(); this.updateTimer();
      this.timer = window.setInterval(() => this.updateTimer(), 250);
      this.message = this.language === 'br' ? 'Enregistrement et brouillon en direct…' : 'Enregistrement en cours…';
      if (this.language === 'br') await this.startLive(this.stream);
    } catch (error) { this.error = error instanceof Error ? error.message : 'Accès au microphone impossible.'; this.cleanup(); }
  }

  stopRecording(): void {
    if (!this.recorder || this.recorder.state !== 'recording') return;
    this.recording = false; this.stopLive(true); this.recorder.stop();
    if (this.timer !== null) window.clearInterval(this.timer); this.timer = null;
  }

  async runWhisper(): Promise<void> {
    if (!this.audioFile || !this.canUseWhisper) return;
    this.busy = true; this.whisperProgress = 2; this.startWhisperProgress(); this.error = ''; this.message = 'Whisper améliore votre texte…';
    try {
      const result = this.language === 'br' ? await this.api.improve(this.audioFile, this.language, this.draft) : await this.api.transcribe(this.audioFile, this.language);
      this.stopWhisperProgress(); this.whisperProgress = 100;
      this.improved = result.text; this.showDraft = false;
      const notices = [
        result.removed_trailing_phrases.length ? 'phrase parasite retirée' : '',
        result.draft_prefix_preserved ? 'début du brouillon Vosk conservé' : '',
      ].filter(Boolean);
      this.message = notices.length ? `Texte amélioré : ${notices.join(' et ')}.` : 'Texte Whisper prêt.';
    } catch (error) { this.stopWhisperProgress(); this.error = this.api.formatError(error); } finally { this.busy = false; }
  }

  reset(): void { this.cleanup(); this.whisperProgress = 0; this.draft = ''; this.improved = ''; this.audioFile = null; if (this.audioUrl) URL.revokeObjectURL(this.audioUrl); this.audioUrl = ''; this.elapsed = '00:00'; this.message = 'Prêt pour un nouvel enregistrement.'; }
  saveAudio(): void { if (this.audioFile) this.download(this.audioFile, this.audioFile.name); }
  saveText(): void { const text = this.transcript.trim(); if (text) this.download(new Blob([`${text}\n`], { type: 'text/plain;charset=utf-8' }), 'keltiawave-record.txt'); }
  saveVoskText(): void { this.saveVersion(this.draft, 'keltiawave-record-vosk.txt'); }
  saveWhisperText(): void { this.saveVersion(this.improved, 'keltiawave-record-whisper.txt'); }
  saveBothTexts(): void {
    const sections = [];
    if (this.draft.trim()) sections.push(`# Version Vosk\n${this.draft.trim()}`);
    if (this.improved.trim()) sections.push(`# Version Whisper\n${this.improved.trim()}`);
    this.saveVersion(sections.join('\n\n'), 'keltiawave-record-vosk-whisper.txt');
  }

  private finalizeRecording(): void {
    const type = this.recorder?.mimeType || 'audio/webm'; const blob = new Blob(this.chunks, { type });
    const ext = type.includes('ogg') ? 'ogg' : type.includes('mp4') ? 'mp4' : 'webm';
    this.audioFile = new File([blob], `keltiawave-record.${ext}`, { type });
    if (this.audioUrl) URL.revokeObjectURL(this.audioUrl); this.audioUrl = URL.createObjectURL(blob);
    this.stream?.getTracks().forEach(track => track.stop()); this.stream = null;
    this.message = this.language === 'br' ? 'Brouillon prêt. Corrigez-le ou améliorez-le avec Whisper.' : 'Audio prêt. Générez maintenant le texte avec Whisper.';
  }

  private async startLive(stream: MediaStream): Promise<void> {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.audioContext = new AudioCtx(); this.source = this.audioContext.createMediaStreamSource(stream); this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.socket = new WebSocket(`${this.api.wsBase}/api/record/live`); this.socket.binaryType = 'arraybuffer';
    this.socket.onopen = () => this.socket?.send(JSON.stringify({ type: 'start', sample_rate: 16000 }));
    this.socket.onmessage = event => this.zone.run(() => this.handleLive(JSON.parse(String(event.data || '{}'))));
    this.socket.onerror = () => this.zone.run(() => { this.error = 'Le brouillon direct est indisponible, mais l’enregistrement continue.'; });
    this.processor.onaudioprocess = event => { if (this.socket?.readyState === WebSocket.OPEN && this.live) this.socket.send(this.downsample(event.inputBuffer.getChannelData(0), this.audioContext?.sampleRate || 48000).buffer); };
    this.source.connect(this.processor); this.processor.connect(this.audioContext.destination);
  }

  private handleLive(payload: { type?: string; text?: string }): void {
    if (payload.type === 'ready') this.live = true;
    if (payload.type === 'partial') this.partial = (payload.text || '').trim();
    if (payload.type === 'final') { this.committed = [this.committed, (payload.text || '').trim()].filter(Boolean).join(' '); this.partial = ''; }
    if (payload.type === 'done') this.live = false;
    this.draft = [this.committed, this.partial].filter(Boolean).join(' ').trim();
  }

  private stopLive(sendStop = false): void {
    if (sendStop && this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: 'stop' })); else this.socket?.close();
    this.processor?.disconnect(); this.source?.disconnect(); if (this.processor) this.processor.onaudioprocess = null;
    this.processor = null; this.source = null; void this.audioContext?.close(); this.audioContext = null; this.live = false;
  }
  private cleanup(): void { this.stopLive(); this.stopWhisperProgress(); this.stream?.getTracks().forEach(track => track.stop()); this.stream = null; if (this.timer !== null) window.clearInterval(this.timer); this.timer = null; }
  private startWhisperProgress(): void {
    this.stopWhisperProgress();
    this.whisperProgressTimer = window.setInterval(() => { this.whisperProgress = Math.min(95, this.whisperProgress + 2); }, 700);
  }
  private stopWhisperProgress(): void { if (this.whisperProgressTimer !== null) window.clearInterval(this.whisperProgressTimer); this.whisperProgressTimer = null; }
  private updateTimer(): void { const seconds = Math.floor((Date.now() - this.startedAt) / 1000); this.elapsed = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`; }
  private pickMime(): string { return ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type)) || ''; }
  private downsample(input: Float32Array, inputRate: number): Int16Array { const ratio = inputRate / 16000; const output = new Int16Array(Math.max(1, Math.round(input.length / ratio))); for (let i = 0; i < output.length; i++) { const value = Math.max(-1, Math.min(1, input[Math.min(input.length - 1, Math.round(i * ratio))] || 0)); output[i] = value < 0 ? value * 0x8000 : value * 0x7fff; } return output; }
  private async loadMicrophones(): Promise<void> { try { this.microphones = (await navigator.mediaDevices?.enumerateDevices() || []).filter(device => device.kind === 'audioinput'); } catch { this.microphones = []; } }
  private download(blob: Blob, name: string): void { const href = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = href; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(href)); }
  private saveVersion(value: string, name: string): void { const text = value.trim(); if (text) this.download(new Blob([`${text}\n`], { type: 'text/plain;charset=utf-8' }), name); }
  private initialInterfaceLanguage(): InterfaceLanguage {
    const query = new URLSearchParams(location.search).get('lang');
    const stored = localStorage.getItem('keltiawave-public-language');
    const value = query || stored || 'en';
    return ['en','fr','br','cy'].includes(value) ? value as InterfaceLanguage : 'en';
  }
}
