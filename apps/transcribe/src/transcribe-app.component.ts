import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { TranscribeApiService, TranscribeLanguage, TranscribeMode, TranscribeResult } from './transcribe-api.service';

type InterfaceLanguage = 'fr' | 'en' | 'br' | 'cy';
const COPY: Record<InterfaceLanguage, Record<string, string>> = {
  fr: {},
  en: {
    'Audio et vidéo vers texte':'Audio and video to text','Autres outils':'Other tools','Transcrire un fichier':'Transcribe a file','Transformez un audio ou une vidéo en texte breton ou gallois.':'Turn Breton or Welsh audio and video into text.','Rapide':'Fast','Fichier non conservé':'File not retained','Mo maximum':'MB maximum','Langue':'Language','Breton':'Breton','Gallois':'Welsh','Cornique':'Cornish','Bientôt':'Soon','Fichier':'File','Déposez votre fichier ici':'Drop your file here','ou cliquez pour le sélectionner':'or click to select it','Mode':'Mode','Brouillon breton immédiat':'Immediate Breton draft','Breton et gallois, meilleure précision':'Breton and Welsh, higher accuracy','Traitement en cours…':'Processing…','Lancer la transcription':'Start transcription','Chargement du fichier':'File upload','Transcription':'Transcription','Temps écoulé':'Elapsed time','Résultat':'Result','Nouveau fichier':'New file','mots':'words','caractères':'characters','Télécharger le texte':'Download text'
  },
  br: {
    'Audio et vidéo vers texte':'Audio ha video da destenn','Autres outils':'Ostilhoù all','Transcrire un fichier':'Treuzskrivañ ur restr','Transformez un audio ou une vidéo en texte breton ou gallois.':'Troit un audio pe ur video e testenn vrezhoneg pe kembraeg.','Rapide':'Buan','Fichier non conservé':'Restr n’eo ket miret','Mo maximum':'Mo d’ar muiañ','Langue':'Yezh','Breton':'Brezhoneg','Gallois':'Kembraeg','Cornique':'Kerneveureg','Bientôt':'A-benn nebeut','Fichier':'Restr','Déposez votre fichier ici':'Lakait ho restr amañ','ou cliquez pour le sélectionner':'pe klikit evit e zibab','Mode':'Mod','Brouillon breton immédiat':'Brouilhed brezhoneg diouzhtu','Breton et gallois, meilleure précision':'Brezhoneg ha kembraeg, resisoc’h','Traitement en cours…':'O tretiñ…','Lancer la transcription':'Kregiñ an treuzskrivadur','Chargement du fichier':'O kargañ ar restr','Transcription':'Treuzskrivadur','Temps écoulé':'Amzer tremenet','Résultat':'Disoc’h','Nouveau fichier':'Restr nevez','mots':'ger','caractères':'arouezenn','Télécharger le texte':'Pellgargañ an destenn'
  },
  cy: {
    'Audio et vidéo vers texte':'Sain a fideo i destun','Autres outils':'Offer eraill','Transcrire un fichier':'Trawsgrifio ffeil','Transformez un audio ou une vidéo en texte breton ou gallois.':'Trowch sain neu fideo Llydaweg neu Gymraeg yn destun.','Rapide':'Cyflym','Fichier non conservé':'Ffeil heb ei chadw','Mo maximum':'MB ar y mwyaf','Langue':'Iaith','Breton':'Llydaweg','Gallois':'Cymraeg','Cornique':'Cernyweg','Bientôt':'Yn fuan','Fichier':'Ffeil','Déposez votre fichier ici':'Gollyngwch eich ffeil yma','ou cliquez pour le sélectionner':'neu cliciwch i’w dewis','Mode':'Modd','Brouillon breton immédiat':'Drafft Llydaweg ar unwaith','Breton et gallois, meilleure précision':'Llydaweg a Chymraeg, mwy cywir','Traitement en cours…':'Wrthi’n prosesu…','Lancer la transcription':'Dechrau trawsgrifio','Chargement du fichier':'Llwytho’r ffeil','Transcription':'Trawsgrifiad','Temps écoulé':'Amser a aeth heibio','Résultat':'Canlyniad','Nouveau fichier':'Ffeil newydd','mots':'gair','caractères':'nod','Télécharger le texte':'Lawrlwytho’r testun'
  }
};

@Component({
  selector: 'transcribe-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transcribe-app.component.html',
  styleUrls: ['./transcribe-app.component.scss', './keltia-footer.scss'],
})
export class TranscribeAppComponent {
  interfaceLanguage: InterfaceLanguage = this.initialInterfaceLanguage();
  language: TranscribeLanguage = 'br';
  mode: TranscribeMode = 'fast';
  file: File | null = null;
  result: TranscribeResult | null = null;
  text = '';
  busy = false;
  dragging = false;
  uploadProgress = 0;
  transcriptionElapsed = 0;
  transcriptionActive = false;
  transcriptionEstimate = 0;
  transcriptionProgress = 0;
  mediaDuration = 0;
  serverRealTimeFactor = 0;
  message = '';
  error = '';
  private request?: Subscription;
  private transcriptionTimer?: ReturnType<typeof setInterval>;

  readonly portalBase = 'http://127.0.0.1:4100/';

  constructor(private readonly api: TranscribeApiService) { this.message = this.status('Choisissez un fichier audio ou vidéo.'); }

  t(source: string): string {
    if (source === 'Qualité') return { fr: 'Qualité', en: 'Quality', br: 'Kalite', cy: 'Ansawdd' }[this.interfaceLanguage];
    return COPY[this.interfaceLanguage][source] || source;
  }
  changeInterfaceLanguage(language: string): void {
    this.interfaceLanguage = language as InterfaceLanguage;
    localStorage.setItem('keltiawave-public-language', this.interfaceLanguage);
    document.documentElement.lang = this.interfaceLanguage;
    if (!this.busy && !this.file) this.message = this.status('Choisissez un fichier audio ou vidéo.');
  }

  get fileSize(): string {
    if (!this.file) return '';
    return this.file.size < 1024 * 1024
      ? `${Math.max(1, Math.round(this.file.size / 1024))} Ko`
      : `${(this.file.size / (1024 * 1024)).toFixed(1)} Mo`;
  }
  get wordCount(): number { return this.text.trim() ? this.text.trim().split(/\s+/).length : 0; }
  get elapsedTime(): string {
    const minutes = Math.floor(this.transcriptionElapsed / 60);
    const seconds = this.transcriptionElapsed % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }
  get remainingTime(): string { return this.formatDuration(Math.max(0, this.transcriptionEstimate - this.transcriptionElapsed)); }
  get estimateExceeded(): boolean { return this.transcriptionEstimate > 0 && this.transcriptionElapsed >= this.transcriptionEstimate; }

  selectLanguage(language: TranscribeLanguage): void {
    if (this.busy) return;
    this.language = language;
    this.mode = language === 'br' ? 'fast' : 'quality';
    this.refreshServerEstimate();
  }

  selectMode(mode: TranscribeMode): void {
    if (this.busy || (this.language === 'cy' && mode === 'fast')) return;
    this.mode = mode;
    this.refreshServerEstimate();
  }

  chooseFile(input: HTMLInputElement): void { this.acceptFile(input.files?.[0] || null); input.value = ''; }
  drop(event: DragEvent): void { event.preventDefault(); this.dragging = false; this.acceptFile(event.dataTransfer?.files?.[0] || null); }

  start(): void {
    if (!this.file || this.busy) return;
    this.busy = true; this.error = ''; this.result = null; this.text = ''; this.uploadProgress = 0; this.transcriptionElapsed = 0; this.transcriptionActive = false; this.transcriptionProgress = 0;
    this.message = this.status('Envoi du fichier…');
    this.request = this.api.transcribe(this.file, this.language, this.mode).subscribe({
      next: event => {
        this.uploadProgress = event.progress;
        if (event.result) {
          this.stopTranscriptionProgress();
          this.transcriptionActive = false;
          this.result = event.result; this.text = event.result.text || ''; this.busy = false;
          this.rememberProcessingSpeed(event.result);
          this.message = `${this.status('Transcription terminée avec')} ${this.mode === 'fast' ? 'Vosk' : 'Whisper'}.`;
        } else if (event.progress < 100) {
          this.message = `${this.status('Envoi du fichier…')} ${event.progress}%`;
        } else {
          this.message = this.status('Transcription en cours…');
          this.startTranscriptionProgress();
        }
      },
      error: error => { this.stopTranscriptionProgress(); this.busy = false; this.error = this.api.formatError(error); },
    });
  }

  reset(): void {
    this.request?.unsubscribe(); this.stopTranscriptionProgress(); this.busy = false; this.file = null; this.result = null; this.text = ''; this.uploadProgress = 0; this.transcriptionElapsed = 0; this.transcriptionActive = false; this.transcriptionEstimate = 0; this.transcriptionProgress = 0; this.mediaDuration = 0; this.serverRealTimeFactor = 0; this.error = '';
    this.mode = this.language === 'br' ? 'fast' : 'quality';
    this.message = this.status('Choisissez un fichier audio ou vidéo.');
  }

  saveText(): void {
    const value = this.text.trim(); if (!value) return;
    const name = `${(this.file?.name || 'transcription').replace(/\.[^.]+$/, '')}.txt`;
    const href = URL.createObjectURL(new Blob([`${value}\n`], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a'); link.href = href; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(href));
  }

  private acceptFile(file: File | null): void {
    if (!file) return;
    if (file.size > 200 * 1024 * 1024) { this.error = this.status('Le fichier dépasse la limite de 200 Mo.'); return; }
    this.file = file; this.result = null; this.text = ''; this.error = ''; this.uploadProgress = 0; this.transcriptionElapsed = 0; this.transcriptionActive = false; this.transcriptionEstimate = 0; this.transcriptionProgress = 0; this.mediaDuration = 0; this.serverRealTimeFactor = 0;
    this.readMediaDuration(file);
    this.message = this.status('Fichier prêt pour la transcription.');
  }

  private startTranscriptionProgress(): void {
    if (this.transcriptionTimer) return;
    this.transcriptionActive = true;
    this.transcriptionElapsed = 0;
    this.transcriptionEstimate = this.estimateProcessingTime();
    this.transcriptionProgress = 0;
    this.transcriptionTimer = setInterval(() => {
      this.transcriptionElapsed += 1;
      if (this.transcriptionEstimate > 0 && !this.estimateExceeded) {
        this.transcriptionProgress = Math.min(99, Math.round(100 * this.transcriptionElapsed / this.transcriptionEstimate));
      }
    }, 1000);
  }

  private stopTranscriptionProgress(): void {
    if (this.transcriptionTimer) clearInterval(this.transcriptionTimer);
    this.transcriptionTimer = undefined;
    this.transcriptionActive = false;
  }

  private estimateProcessingTime(): number {
    if (!this.mediaDuration) return 0;
    const stored = Number(localStorage.getItem(this.speedProfileKey));
    const realTimeFactor = this.serverRealTimeFactor > 0
      ? this.serverRealTimeFactor
      : Number.isFinite(stored) && stored > 0 ? stored : (this.mode === 'fast' ? 0.45 : 1.25);
    return Math.max(2, Math.round(this.mediaDuration * realTimeFactor));
  }

  private rememberProcessingSpeed(result: TranscribeResult): void {
    const metrics = result.metrics as { processing_time?: { seconds?: number } } | undefined;
    const seconds = Number(metrics?.processing_time?.seconds);
    if (!this.mediaDuration || !Number.isFinite(seconds) || seconds <= 0) return;
    const observed = seconds / this.mediaDuration;
    const previous = Number(localStorage.getItem(this.speedProfileKey));
    const calibrated = Number.isFinite(previous) && previous > 0 ? previous * 0.65 + observed * 0.35 : observed;
    localStorage.setItem(this.speedProfileKey, String(Math.max(0.05, Math.min(10, calibrated))));
  }

  private get speedProfileKey(): string { return `keltiawave-transcribe-rtf-${this.language}-${this.mode}`; }

  private readMediaDuration(file: File): void {
    const media = document.createElement(file.type.startsWith('video/') ? 'video' : 'audio');
    const url = URL.createObjectURL(file);
    media.preload = 'metadata';
    media.onloadedmetadata = () => {
      this.mediaDuration = Number.isFinite(media.duration) ? media.duration : 0;
      this.refreshServerEstimate();
      URL.revokeObjectURL(url);
    };
    media.onerror = () => URL.revokeObjectURL(url);
    media.src = url;
  }

  private refreshServerEstimate(): void {
    if (!this.mediaDuration || this.busy) return;
    this.api.estimate(this.language, this.mode, this.mediaDuration).subscribe({
      next: estimate => { this.serverRealTimeFactor = Number(estimate.real_time_factor) || 0; },
      error: () => { this.serverRealTimeFactor = 0; },
    });
  }

  private formatDuration(totalSeconds: number): string {
    const seconds = Math.max(0, Math.round(totalSeconds));
    const minutes = Math.floor(seconds / 60);
    return minutes ? `${minutes} min ${String(seconds % 60).padStart(2, '0')} s` : `${seconds} s`;
  }

  private initialInterfaceLanguage(): InterfaceLanguage {
    const query = new URLSearchParams(location.search).get('lang');
    const stored = localStorage.getItem('keltiawave-public-language');
    const value = query || stored || 'fr';
    return ['fr','en','br','cy'].includes(value) ? value as InterfaceLanguage : 'fr';
  }

  private status(source: string): string {
    const statuses: Record<InterfaceLanguage, Record<string,string>> = {
      fr:{},
      en:{'Choisissez un fichier audio ou vidéo.':'Choose an audio or video file.','Envoi du fichier…':'Uploading file…','Transcription en cours…':'Transcription in progress…','Transcription terminée avec':'Transcription completed with','Le fichier dépasse la limite de 200 Mo.':'The file exceeds the 200 MB limit.','Fichier prêt pour la transcription.':'File ready for transcription.'},
      br:{'Choisissez un fichier audio ou vidéo.':'Dibabit ur restr audio pe video.','Envoi du fichier…':'O kargañ ar restr…','Transcription en cours…':'O treuzskrivañ…','Transcription terminée avec':'Treuzskrivadur echuet gant','Le fichier dépasse la limite de 200 Mo.':'Brasoc’h eo ar restr eget 200 Mo.','Fichier prêt pour la transcription.':'Prest eo ar restr da vezañ treuzskrivet.'},
      cy:{'Choisissez un fichier audio ou vidéo.':'Dewiswch ffeil sain neu fideo.','Envoi du fichier…':'Wrthi’n llwytho’r ffeil…','Transcription en cours…':'Wrthi’n trawsgrifio…','Transcription terminée avec':'Trawsgrifiad wedi’i gwblhau gyda','Le fichier dépasse la limite de 200 Mo.':'Mae’r ffeil yn fwy na’r terfyn 200 MB.','Fichier prêt pour la transcription.':'Ffeil yn barod i’w thrawsgrifio.'}
    };
    return statuses[this.interfaceLanguage][source] || source;
  }
}
