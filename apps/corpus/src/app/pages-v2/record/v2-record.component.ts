import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom, forkJoin } from 'rxjs';
import { ApiService, AudioRead, Phrase } from '../../core/api.service';
import { AudioRecorderService } from '../../core/audio-recorder.service';
import { AuthService } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

@Component({
  selector: 'app-v2-record',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-record.component.html',
  styleUrls: ['./v2-record.component.scss'],
})
export class V2RecordComponent implements OnInit, OnDestroy {
  phrases: Phrase[] = [];
  currentPhrase: Phrase | null = null;
  loading = true;
  submitting = false;
  error: string | null = null;
  success: string | null = null;

  durationSec = 0;
  blobUrl: string | null = null;
  lastBlob: Blob | null = null;
  speakerRegion = '';
  speakerLevel = '';

  private readonly completedPhraseIds = new Set<number>();

  private timer?: ReturnType<typeof setInterval>;

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
    private readonly route: ActivatedRoute,
    private readonly recorder: AudioRecorderService,
    private readonly zone: NgZone,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadPhrase();
  }

  ngOnDestroy(): void {
    this.clearTimer();
    this.recorder.dispose();
    this.revokeBlobUrl();
  }

  get isRecording(): boolean {
    return this.recorder.isRecording;
  }

  get phrasePosition(): string {
    if (!this.currentPhrase || !this.phrases.length) return `${this.i18n.translate('home.phrase')} 0 / 0`;
    const index = this.phrases.findIndex((phrase) => phrase.id === this.currentPhrase?.id);
    return `${this.i18n.translate('home.phrase')} ${Math.max(index, 0) + 1} / ${this.phrases.length}`;
  }

  get completionPosition(): string {
    return `${this.completedCount} / ${this.phrases.length}`;
  }

  get progressPercent(): number {
    if (!this.phrases.length) return 0;
    return Math.round((this.completedCount / this.phrases.length) * 100);
  }

  private get completedCount(): number {
    return this.phrases.reduce((count, phrase) => count + Number(this.completedPhraseIds.has(phrase.id)), 0);
  }

  get classLabel(): string {
    const user = this.auth.user();
    if (!user) return this.i18n.translate('v2.classNotConnected');
    const organization = (user.school || user.organization)?.trim();
    if (!organization) return this.i18n.translate('v2.classNotMember');
    return organization;
  }

  get hasClassContext(): boolean {
    const user = this.auth.user();
    return !!user?.organization?.trim() || !!user?.school?.trim();
  }

  get classHelp(): string {
    const user = this.auth.user();
    if (!user) return this.i18n.translate('v2.classLoginHelp');
    const organization = (user.school || user.organization)?.trim();
    if (!organization) return this.i18n.translate('v2.classMemberHelp');
    return this.i18n.translate('v2.classOpenHelp');
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      void this.loadPhrase();
    }
  }

  async startRecording(): Promise<void> {
    if (!this.currentPhrase || this.submitting) return;
    this.error = null;
    this.success = null;
    this.revokeBlobUrl();
    this.lastBlob = null;
    this.durationSec = 0;

    try {
      await this.recorder.init();
      this.recorder.start(1000);
      this.clearTimer();
      this.timer = setInterval(() => {
        this.zone.run(() => {
          this.durationSec += 1;
          this.cdr.markForCheck();
        });
      }, 1000);
    } catch {
      this.error = 'Acces au micro impossible. Verifie les permissions du navigateur.';
    }
  }

  async stopRecording(): Promise<void> {
    try {
      const blob = await this.recorder.stop();
      this.clearTimer();
      this.lastBlob = blob;
      this.blobUrl = URL.createObjectURL(blob);
    } catch {
      this.clearTimer();
      this.error = 'Arret de l’enregistrement impossible.';
    }
  }

  resetRecording(): void {
    this.clearTimer();
    this.recorder.dispose();
    this.revokeBlobUrl();
    this.lastBlob = null;
    this.durationSec = 0;
    this.error = null;
    this.success = null;
  }

  previousPhrase(): void {
    this.selectRelativePhrase(-1);
  }

  nextPhrase(): void {
    this.selectRelativePhrase(1);
  }

  async submitRecording(): Promise<void> {
    if (!this.currentPhrase || !this.lastBlob || this.submitting) return;
    this.submitting = true;
    this.error = null;
    this.success = null;

    try {
      const recordedPhraseId = this.currentPhrase.id;
      await firstValueFrom(this.api.uploadAudio(
        this.currentPhrase.id,
        this.lastBlob,
        `phrase-${this.currentPhrase.id}.webm`,
        {
          phraseSource: 'suggested',
          domain: this.currentPhrase.theme || undefined,
          speakerRegion: this.speakerRegion || undefined,
          speakerLevel: this.speakerLevel || undefined,
        },
      ));
      this.completedPhraseIds.add(recordedPhraseId);
      this.resetRecording();
      this.success = 'Enregistrement envoye. Il apparait maintenant dans la file d’evaluation.';
      this.moveToNextPhrase();
    } catch (err: any) {
      this.error = err?.error?.detail || err?.message || 'Upload impossible pour le moment.';
    } finally {
      this.submitting = false;
      this.cdr.markForCheck();
    }
  }

  mmss(seconds: number): string {
    const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
    const rest = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${minutes}:${rest}`;
  }

  private async loadPhrase(): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      const phraseId = Number(this.route.snapshot.queryParamMap.get('phraseId') || 0);
      // La langue de l'interface (FR/EN/BR/CY) ne doit pas changer le corpus
      // actif : cette page est le parcours de lecture du corpus breton.
      const phrasesRequest = this.api.getPhrases('br');
      const userEmail = this.auth.user()?.email?.trim().toLowerCase();
      let phrases: Phrase[];
      let audios: AudioRead[] = [];

      if (userEmail) {
        const result = await firstValueFrom(forkJoin({
          phrases: phrasesRequest,
          approved: this.api.listAudios('approved'),
          pending: this.api.listAudios('pending'),
          rejected: this.api.listAudios('rejected'),
        }));
        phrases = result.phrases;
        audios = [...result.approved, ...result.pending, ...result.rejected];
      } else {
        phrases = await firstValueFrom(phrasesRequest);
      }

      this.phrases = this.uniquePhrases(phrases);
      this.completedPhraseIds.clear();
      audios
        .filter((audio) => audio.contributor_email?.trim().toLowerCase() === userEmail)
        .forEach((audio) => this.completedPhraseIds.add(audio.phrase_id));

      this.currentPhrase = this.phrases.find((phrase) => phrase.id === phraseId)
        ?? this.phrases.find((phrase) => !this.completedPhraseIds.has(phrase.id))
        ?? this.phrases[0]
        ?? null;
      if (!this.currentPhrase) {
        this.error = 'Aucune phrase bretonne disponible pour l’enregistrement.';
      }
    } catch (err: any) {
      this.error = err?.error?.detail || err?.message || 'Chargement de la phrase impossible.';
    } finally {
      this.loading = false;
      this.cdr.markForCheck();
    }
  }

  private clearTimer(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  private revokeBlobUrl(): void {
    if (this.blobUrl) {
      URL.revokeObjectURL(this.blobUrl);
      this.blobUrl = null;
    }
  }

  private moveToNextPhrase(): void {
    if (!this.currentPhrase || !this.phrases.length) return;
    const index = this.phrases.findIndex((phrase) => phrase.id === this.currentPhrase?.id);
    for (let offset = 1; offset <= this.phrases.length; offset += 1) {
      const candidate = this.phrases[(Math.max(index, 0) + offset) % this.phrases.length];
      if (!this.completedPhraseIds.has(candidate.id)) {
        this.currentPhrase = candidate;
        return;
      }
    }
    this.currentPhrase = this.phrases[(Math.max(index, 0) + 1) % this.phrases.length];
  }

  private selectRelativePhrase(offset: -1 | 1): void {
    if (!this.currentPhrase || this.phrases.length < 2 || this.isRecording || this.submitting) return;
    const index = this.phrases.findIndex((phrase) => phrase.id === this.currentPhrase?.id);
    const nextIndex = (Math.max(index, 0) + offset + this.phrases.length) % this.phrases.length;
    this.resetRecording();
    this.currentPhrase = this.phrases[nextIndex];
  }

  private uniquePhrases(phrases: Phrase[]): Phrase[] {
    const seen = new Set<string>();
    return phrases.filter((phrase) => {
      const key = phrase.texte.trim().toLowerCase().replace(/\s+/g, ' ');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}
