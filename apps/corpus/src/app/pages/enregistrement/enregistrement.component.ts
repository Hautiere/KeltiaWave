import { CommonModule } from '@angular/common';
import { Component, ChangeDetectorRef, NgZone, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AudioRecorderService } from '../../core/audio-recorder.service';
import { ApiService, type Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { I18nService } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { DOMAIN_OPTIONS, domainLabelKey } from '../../core/domains';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  selector: 'app-enregistrement',
  templateUrl: './enregistrement.component.html',
  styleUrls: ['./enregistrement.component.scss']
})
export class EnregistrementComponent implements OnInit, OnDestroy {
  durationSec = 0;
  private timer?: any;

  blobUrl: string | null = null;
  lastBlob: Blob | File | null = null;

  phraseId = 0;
  phraseText = '';
  phraseMode: 'suggested' | 'custom' = 'suggested';
  customPhrase = '';
  loadingPhrase = false;
  phraseError: string | null = null;
  speakerRegion = '';
  speakerLevel = '';
  domain = '';
  submitting = false;
  statusMessage: string | null = null;
  statusKind: 'success' | 'error' | null = null;
  private statusTimer?: any;
  readonly regions = [
    { value: '', label: 'Non definie' },
    { value: 'bro-dreger', label: 'Tregor' },
    { value: 'bro-leon', label: 'Leon' },
    { value: 'bro-gernev', label: 'Cornouaille' },
    { value: 'bro-wened', label: 'Vannetais' },
    { value: 'bro-saint-brieuc', label: 'Pays de Saint-Brieuc' },
    { value: 'other', label: 'Autre / pas sur' },
  ];
  readonly levels = [
    { value: '', labelKey: 'level.undefined' },
    { value: 'beginner', labelKey: 'level.beginner' },
    { value: 'intermediate', labelKey: 'level.intermediate' },
    { value: 'advanced', labelKey: 'level.advanced' },
    { value: 'native-heritage', labelKey: 'level.nativeFamily' },
  ];
  readonly editableDomains = DOMAIN_OPTIONS.filter((domain) => !!domain.value);

  constructor(
    private rec: AudioRecorderService,
    private api: ApiService,
    readonly auth: AuthService,
    private i18n: I18nService,
    private cdr: ChangeDetectorRef,
    private zone: NgZone
  ) {}

  ngOnInit(): void {
    this.loadRandomPhrase();
  }

  get isRecording(): boolean {
    return this.rec.isRecording;
  }

  get isDragonTheme(): boolean {
    return false;
  }

  get isBlueTriskell(): boolean {
    const language = this.i18n.language();
    return language === 'en' || language === 'cy';
  }

  get canEditDomains(): boolean {
    return this.auth.user()?.role === 'admin';
  }

  domainLabel(value?: string | null): string {
    const values = this.parseDomains(value);
    if (!values.length) return this.i18n.translate('domain.undefined');
    return values.map((item) => this.i18n.translate(domainLabelKey(item))).join(', ');
  }

  isDomainSelected(value: string): boolean {
    return this.parseDomains(this.domain).includes(value);
  }

  toggleDomain(value: string): void {
    if (this.isRecording || this.submitting) return;
    const selected = this.parseDomains(this.domain);
    this.domain = selected.includes(value)
      ? selected.filter((item) => item !== value).join(',')
      : [...selected, value].join(',');
  }

  ngOnDestroy(): void {
    this.clearTimer();
    this.clearStatusTimer();
    this.rec.dispose();
    if (this.blobUrl) URL.revokeObjectURL(this.blobUrl);
  }

  private clearTimer() {
    if (this.timer) { clearInterval(this.timer); this.timer = undefined; }
  }

  private clearStatusTimer() {
    if (this.statusTimer) { clearTimeout(this.statusTimer); this.statusTimer = undefined; }
  }

  private showStatus(kind: 'success' | 'error', message: string) {
    this.clearStatusTimer();
    this.statusKind = kind;
    this.statusMessage = message;
    this.statusTimer = setTimeout(() => {
      this.statusMessage = null;
      this.statusKind = null;
      this.cdr.markForCheck();
    }, 5000);
    this.cdr.markForCheck();
  }

  async loadRandomPhrase(force = false) {
    if (this.isRecording) return;
    this.phraseMode = 'suggested';
    this.loadingPhrase = true;
    this.phraseError = null;
    this.cdr.markForCheck();

    try {
      const list: Phrase[] = await firstValueFrom(this.api.getPhrases());
      if (!list?.length) {
        this.phraseId = 0;
        this.phraseText = this.i18n.translate('record.noPhrase');
      } else {
        const pick = list[Math.floor(Math.random() * list.length)];
        this.phraseId = pick.id;
        this.phraseText = pick.texte ?? '';
        this.domain = pick.theme ?? '';
      }
    } catch {
      this.phraseError = this.i18n.translate('record.loadError');
    } finally {
      this.loadingPhrase = false;
      this.cdr.markForCheck();
    }
  }

  async startRec() {
    try {
      this.statusMessage = null;
      this.statusKind = null;
      if (!this.canRecord()) {
        this.showStatus('error', this.i18n.translate('record.needPhrase'));
        return;
      }
      if (this.phraseMode === 'suggested' && !this.phraseId) await this.loadRandomPhrase(true);
      await this.rec.init();
      this.rec.start(1000);
      this.durationSec = 0;
      this.clearTimer();
      this.timer = setInterval(() => {
        this.zone.run(() => {
          this.durationSec++;
          this.cdr.markForCheck();
        });
      }, 1000);

      if (this.blobUrl) URL.revokeObjectURL(this.blobUrl);
      this.blobUrl = null;
      this.lastBlob = null;
    } catch {
      this.showStatus('error', this.i18n.translate('record.microError'));
    }
  }

  async stopRec() {
    try {
      const blob = await this.rec.stop();
      this.clearTimer();
      this.lastBlob = blob;
      this.blobUrl = URL.createObjectURL(blob);
      this.cdr.markForCheck();
    } catch {
      this.clearTimer();
    }
  }

  cancel() {
    this.clearTimer();
    this.rec.dispose();
    if (this.blobUrl) URL.revokeObjectURL(this.blobUrl);
    this.blobUrl = null;
    this.lastBlob = null;
  }

  retry(): void {
    if (this.blobUrl) { try { URL.revokeObjectURL(this.blobUrl); } catch {} }
    this.blobUrl = null;
    this.lastBlob = null;
    this.durationSec = 0;
  }

  mmss(s: number) {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const ss = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${ss}`;
  }

  async submit() {
    if (!this.lastBlob || this.submitting) return;
    try {
      this.submitting = true;
      this.statusMessage = null;
      this.statusKind = null;
      const phraseId = await this.resolvePhraseId();
      if (!phraseId) {
        this.showStatus('error', this.i18n.translate('record.needPhraseSubmit'));
        return;
      }
      await firstValueFrom(this.api.uploadAudio(phraseId, this.lastBlob, 'recording.webm', {
        phraseSource: this.phraseMode,
        domain: this.domain || undefined,
        speakerRegion: this.speakerRegion || undefined,
        speakerLevel: this.speakerLevel || undefined,
      }));
      this.cancel();
      if (this.phraseMode === 'custom') {
        this.customPhrase = '';
      }
      await this.loadRandomPhrase(true);
      this.showStatus('success', this.i18n.translate('record.uploadOk'));
    } catch {
      this.showStatus('error', this.i18n.translate('record.uploadError'));
    } finally {
      this.submitting = false;
      this.cdr.markForCheck();
    }
  }

  setPhraseMode(mode: 'suggested' | 'custom') {
    if (this.isRecording || this.submitting) return;
    this.phraseMode = mode;
    this.statusMessage = null;
    this.statusKind = null;
  }

  canRecord(): boolean {
    if (this.phraseMode === 'custom') return this.customPhrase.trim().length >= 2;
    return !!this.phraseId;
  }

  private async resolvePhraseId(): Promise<number> {
    if (this.phraseMode === 'suggested') return this.phraseId;

    const text = this.customPhrase.trim();
    if (!text) return 0;
    const phrase = await firstValueFrom(this.api.createPhrase({
      texte: text,
      theme: this.domain || null,
      langue: 'br',
      auteur: 'contributor',
    }));
    return phrase.id;
  }

  private parseDomains(value?: string | null): string[] {
    return (value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }
}
