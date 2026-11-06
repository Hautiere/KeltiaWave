import { mobileToolLinks, mobileLabel, mobileLiveText } from '../../shared/mobile-tools';
import { Component, ElementRef, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LiveAudioService, LiveEvent, LiveLanguage, LiveCapabilities } from './live-audio.service';

type State = 'idle' | 'starting' | 'listening' | 'paused' | 'stopping';

@Component({
  selector: 'live-root', standalone: true, imports:[FormsModule],
  templateUrl: './live-app.component.html', styleUrl: './live-app.component.scss',
})
export class LiveAppComponent implements OnInit, OnDestroy {
  get mobileLinks() { return mobileToolLinks(); }
  mobileLabel(key: string): string { return mobileLabel(key, this.mobileInterfaceLanguage); }
  mobileText(source: string): string { return window.matchMedia('(max-width:700px)').matches ? mobileLiveText(source, this.mobileInterfaceLanguage) : source; }
  mobileInterfaceLanguage = typeof localStorage === 'undefined' ? 'fr' : localStorage.getItem('keltiawave-public-language') || 'fr';
  changeMobileInterfaceLanguage(value: string): void {
    if (!['fr','en','br','cy'].includes(value)) return;
    this.mobileInterfaceLanguage = value;
    localStorage.setItem('keltiawave-public-language', value);
  }

  @ViewChild('transcript') transcript?: ElementRef<HTMLDivElement>;
  state: State = 'idle';
  language:LiveLanguage='br';
  resultLanguage:LiveLanguage='br';
  private capabilities:LiveCapabilities|null=null;
  private capabilitiesSequence=0;
  get engine():string {return this.language==='cy'?'W2V':'Vosk';}
  get resultEngine():string {return this.resultLanguage==='cy'?'W2V':'Vosk';}
  selectLanguage(language:LiveLanguage):void {if(this.busy)return;this.language=language;void this.checkServer();}
  available: boolean | null = null;
  whisperAvailable = false;
  improving = false;
  whisperUpload: number | null = 0;
  whisperProcessing = false;
  whisperEstimate = 0;
  whisperElapsed = 0;
  private whisperTimer: number | null = null;
  private whisperSequence = 0;
  get whisperIndeterminate(): boolean { return !this.whisperEstimate || this.whisperElapsed >= this.whisperEstimate; }
  get whisperProgress(): number { return this.whisperEstimate ? Math.min(99, Math.round(this.whisperElapsed / this.whisperEstimate * 100)) : 0; }
  get whisperElapsedTime(): string { return this.formatWhisperTime(this.whisperElapsed); }
  get whisperRemainingTime(): string { return this.formatWhisperTime(Math.max(0, this.whisperEstimate - this.whisperElapsed)); }
  private formatWhisperTime(seconds: number): string {
    const value = Math.ceil(seconds);
    return `${Math.floor(value / 60).toString().padStart(2, '0')}:${(value % 60).toString().padStart(2, '0')}`;
  }
  private stopWhisperProgress(): void {
    if (this.whisperTimer !== null) window.clearInterval(this.whisperTimer);
    this.whisperTimer = null;
  }
  whisperText: string | null = null;
  version: 'vosk' | 'whisper' = 'vosk';
  whisperError = '';
  error = '';
  notice = '';
  segments: string[] = [];
  partial = '';
  follow = true;
  level = 0;
  seconds = 0;
  private clock: number | null = null;
  private lastSound = 0;
  private silence = false;
  private startSequence = 0;
  readonly bars = Array.from({ length: 38 }, (_, index) => index);
  readonly portalHref = ['localhost', '127.0.0.1'].includes(location.hostname)
    ? 'http://127.0.0.1:4100/' : location.hostname.includes('.staging.') ? 'https://staging.keltiawave.com/' : 'https://keltiawave.com/';

  constructor(readonly audio: LiveAudioService, private readonly zone: NgZone) {}
  ngOnInit(): void { void this.checkServer(); }
  async checkServer(): Promise<void> {
    const sequence=++this.capabilitiesSequence;
    this.available = null; this.error = '';
    try {
      const capabilities = await this.audio.capabilities();
      if(sequence!==this.capabilitiesSequence) return;
      this.capabilities=capabilities;
      this.available = capabilities.languages[this.language]?.live ?? false;
      this.whisperAvailable = capabilities.languages[this.text ? this.resultLanguage : this.language]?.whisper ?? false;
    }
    catch { if(sequence!==this.capabilitiesSequence)return;this.available = false; this.error = 'Impossible de joindre le serveur Live. Réessayez dans un instant.'; }
  }
  get busy(): boolean { return this.state !== 'idle' || this.improving; }
  get voskText(): string { return [...this.segments, this.partial].filter(Boolean).join('\n\n'); }
  get text(): string { return this.version === 'whisper' ? this.whisperText || '' : this.voskText; }
  get elapsed(): string { return `${Math.floor(this.seconds / 60).toString().padStart(2, '0')}:${(this.seconds % 60).toString().padStart(2, '0')}`; }
  get status(): string {
    if (this.improving) return 'Traitement Whisper…';
    if (this.state === 'starting') return 'Choisissez la source audio…';
    if (this.state === 'stopping') return 'Finalisation du texte…';
    if (this.state === 'paused') return 'En pause';
    if (this.state === 'listening') return this.silence ? 'Aucun son détecté' : 'En écoute';
    return this.text ? 'Écoute terminée' : 'Prêt à écouter';
  }
  async start(): Promise<void> {
    if (this.busy || !this.audio.supported || !this.available) return;
    // Keep the previous transcript until the new capture has actually started.
    const sequence = ++this.startSequence;
    const language=this.language;
    this.state = 'starting'; this.error = ''; this.notice = '';
    try {
      await this.audio.start(
        event => this.zone.run(() => this.receive(event)),
        level => this.zone.run(() => { this.level = level; if (level > .003) this.lastSound = Date.now(); }),
        () => this.zone.run(() => this.ended()),
        language,
      );
      if (sequence !== this.startSequence || this.state !== 'starting') return;
      this.segments = []; this.partial = ''; this.seconds = 0; this.follow = true;
      this.whisperText = null; this.version = 'vosk'; this.whisperError = '';
      this.resultLanguage=language;this.whisperAvailable=this.capabilities?.languages[language]?.whisper ?? false;
      this.state = 'listening'; this.silence = false; this.lastSound = Date.now();
      this.clock = window.setInterval(() => {
        if (this.state === 'listening') { this.seconds++; this.silence = Date.now() - this.lastSound > 5000; }
      }, 1000);
    } catch (error) {
      if (sequence !== this.startSequence) return;
      this.state = 'idle';
      this.error = error instanceof DOMException && error.name === 'NotAllowedError'
        ? 'Partage annulé ou refusé. Pour réessayer, autorisez le partage de l’onglet avec son audio.'
        : error instanceof Error ? error.message : 'Le partage audio n’a pas pu démarrer.';
    }
  }
  pause(): void {
    if (!['listening', 'paused'].includes(this.state)) return;
    this.state = this.state === 'paused' ? 'listening' : 'paused';
    this.audio.pause(this.state === 'paused'); this.level = 0; this.lastSound = Date.now();
  }
  async improve(): Promise<void> {
    if (this.busy || !this.whisperAvailable || !this.audio.whisperAudio) return;
    const sequence = ++this.whisperSequence;
    this.improving = true; this.whisperError = ''; this.notice = '';
    this.whisperUpload = 0; this.whisperProcessing = false; this.whisperElapsed = 0; this.whisperEstimate = 0;
    void this.audio.whisperEstimate(this.seconds).then(estimate => {
      if (sequence === this.whisperSequence && this.improving) this.whisperEstimate = estimate;
    });
    try {
      const result = await this.audio.improve(progress => {
        if (sequence !== this.whisperSequence) return;
        this.whisperUpload = progress;
        if (progress === 100 && !this.whisperProcessing) {
          this.whisperProcessing = true;
          const started = Date.now();
          this.whisperTimer = window.setInterval(() => { this.whisperElapsed = Math.floor((Date.now() - started) / 1000); }, 1000);
        }
      });
      if (sequence !== this.whisperSequence) return;
      if (!result.text.trim()) {
        this.whisperError = 'Whisper n’a pas reconnu de paroles. La version '+this.resultEngine+' est conservée.';
        return;
      }
      this.whisperText = result.text; this.version = 'whisper'; this.follow = true;
      this.scrollToLive();
    } catch {
      if (sequence !== this.whisperSequence) return;
      this.whisperError = 'Whisper est indisponible ou le traitement a échoué. La version '+this.resultEngine+' est conservée ; vous pouvez réessayer.';
    } finally { if (sequence === this.whisperSequence) { this.stopWhisperProgress(); this.improving = false; } }
  }
  stop(): void {
    if (!this.busy || this.state === 'stopping') return;
    ++this.startSequence;
    this.state = 'stopping'; void this.audio.stop();
  }
  private receive(event: LiveEvent): void {
    if (event.type === 'partial') this.partial = event.text || '';
    if (event.type === 'final') { if (event.text) this.segments.push(event.text); this.partial = ''; }
    if (event.type === 'error') this.error = event.message || 'La transcription a été interrompue.';
    this.scrollToLive();
  }
  private ended(): void {
    this.state = 'idle'; this.level = 0;
    if (this.clock !== null) window.clearInterval(this.clock); this.clock = null;
  }
  onScroll(): void {
    const element = this.transcript?.nativeElement;
    if (element) this.follow = element.scrollHeight - element.scrollTop - element.clientHeight < 60;
  }
  returnToLive(): void { this.follow = true; this.scrollToLive(); }
  private scrollToLive(): void {
    if (!this.follow) return;
    requestAnimationFrame(() => {
      const element = this.transcript?.nativeElement;
      if (element && this.follow) element.scrollTop = element.scrollHeight;
    });
  }
  async copy(): Promise<void> {
    try { await navigator.clipboard.writeText(this.text); this.notice = 'Texte copié.'; }
    catch { this.notice = 'Copie indisponible. Vous pouvez sélectionner le texte pour le copier.'; }
  }
  save(): void {
    const url = URL.createObjectURL(new Blob([this.text + '\n'], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'keltiawave-live.txt'; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async share(): Promise<void> {
    if (!navigator.share) { await this.copy(); return; }
    try { await navigator.share({ title: 'KeltiaWave Live', text: this.text }); }
    catch (error) { if (!(error instanceof DOMException && error.name === 'AbortError')) this.notice = 'Partage indisponible. Copiez ou enregistrez le texte.'; }
  }
  ngOnDestroy(): void { ++this.capabilitiesSequence; ++this.whisperSequence; this.stopWhisperProgress(); ++this.startSequence; this.audio.destroy(); this.ended(); }
}
