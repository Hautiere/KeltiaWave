import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom, forkJoin } from 'rxjs';
import { audioFileUrl } from '../../core/constants';
import { ApiService, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { ProfileService } from '../../core/profile.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { AudioRead } from '../../core/models';
import { ValidationsService } from '../../core/validations.service';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

@Component({
  selector: 'app-v2-evaluate',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-evaluate.component.html',
  styleUrls: ['./v2-evaluate.component.scss'],
})
export class V2EvaluateComponent implements OnInit {
  private allAudios: AudioRead[] = [];
  audios: AudioRead[] = [];
  selectedClass = '';
  selectedIndex = 0;
  currentPhrase: Phrase | null = null;
  loading = true;
  acting = false;
  error: string | null = null;
  success: string | null = null;
  playbackError: string | null = null;
  comment = '';
  pronunciationLevel = '';
  pronunciationRegion = '';
  readonly pronunciationLevels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'native'];
  readonly pronunciationRegions = ['Kerne (Cornouaille)', 'Leon (Léon)', 'Treger (Trégor)', 'Gwened (Vannetais)', 'Autre'];

  @ViewChild('player') private playerRef?: ElementRef<HTMLAudioElement>;

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    readonly profileService: ProfileService,
    private readonly api: ApiService,
    private readonly validations: ValidationsService,
    private readonly cdr: ChangeDetectorRef,
    private readonly route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.loadAudios();
  }

  get current(): AudioRead | null {
    return this.audios[this.selectedIndex] ?? null;
  }

  get classOptions(): string[] {
    const assigned = this.teacherClassNames;
    const audioClasses = this.allAudios
      .map((audio) => audio.contributor_school?.trim())
      .filter((value): value is string => !!value);
    const available = assigned.length
      ? audioClasses.filter((name) => assigned.some((item) => this.canonicalClass(item) === this.canonicalClass(name)))
      : audioClasses;
    return Array.from(new Set(available));
  }

  get isTeacher(): boolean {
    return this.auth.user()?.role === 'teacher';
  }

  get canEvaluate(): boolean {
    const role = this.auth.user()?.role;
    return role === 'teacher' || role === 'admin';
  }

  get feedbackView(): boolean {
    return this.route.snapshot.queryParamMap.get('feedback') === 'true' || !this.canEvaluate;
  }

  get queuePosition(): string {
    if (!this.audios.length) return `${this.i18n.translate('adminData.recordings')} 0 / 0`;
    return `${this.i18n.translate('adminData.recordings')} ${this.selectedIndex + 1} / ${this.audios.length}`;
  }

  get currentAudioPosition(): string {
    if (!this.audios.length) return '0 / 0';
    return `${this.selectedIndex + 1} / ${this.audios.length}`;
  }

  get progressPercent(): number {
    if (!this.audios.length) return 0;
    return Math.round(((this.selectedIndex + 1) / this.audios.length) * 100);
  }

  validationCount(audio: AudioRead | null): number {
    return audio?.validations?.length ?? 0;
  }

  statusLabel(audio: AudioRead | null): string {
    if (!audio) return '';
    if (audio.status === 'pending') return this.i18n.translate('adminData.pending');
    if (audio.status === 'approved') return this.i18n.translate('corpus.valid');
    return this.i18n.translate('adminData.rejected');
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      this.loadPhrase();
    }
  }

  audioUrl(audio: AudioRead | null): string {
    return audio ? audioFileUrl(audio.id) : '';
  }

  async playCurrent(): Promise<void> {
    const player = this.playerRef?.nativeElement;
    const current = this.current;
    if (!player || !current) return;

    this.playbackError = null;
    const src = this.audioUrl(current);
    if (player.src !== new URL(src, window.location.origin).href) {
      player.src = src;
      player.load();
    }

    if (!player.paused) {
      player.pause();
      return;
    }

    try {
      await player.play();
    } catch {
      this.playbackError = this.i18n.translate('validation.audioMissing');
      this.cdr.markForCheck();
    }
  }

  onAudioError(): void {
    this.playbackError = this.i18n.translate('validation.audioMissing');
    this.cdr.markForCheck();
  }

  select(index: number): void {
    if (this.acting || index === this.selectedIndex) return;
    this.selectedIndex = index;
    this.loadExistingComment();
    this.success = null;
    this.error = null;
    this.playbackError = null;
    this.loadPhrase();
    setTimeout(() => this.reloadPlayer());
  }

  next(): void {
    if (!this.audios.length || this.acting) return;
    this.select((this.selectedIndex + 1) % this.audios.length);
  }

  selectClass(value: string): void {
    this.selectedClass = value;
    this.applyClassFilter();
  }

  async saveComment(): Promise<void> {
    const current = this.current;
    const cleanedComment = this.comment.trim();
    if (!current || !cleanedComment || this.acting) return;
    this.acting = true;
    this.error = null;
    this.success = null;
    try {
      const updated = await firstValueFrom(this.validations.comment(current.id, cleanedComment));
      this.replaceAudio(updated);
      this.loadExistingComment();
      this.success = 'Commentaire du professeur enregistré.';
    } catch (err: any) {
      this.error = err?.error?.detail || err?.message || 'Enregistrement du commentaire impossible.';
    } finally {
      this.acting = false;
      this.cdr.markForCheck();
    }
  }

  async approve(): Promise<void> {
    await this.decide(true);
  }

  async reject(): Promise<void> {
    await this.decide(false);
  }

  private loadAudios(): void {
    this.loading = true;
    this.error = null;
    forkJoin({
      pending: this.validations.listByStatus('pending'),
      approved: this.validations.listByStatus('approved'),
      rejected: this.validations.listByStatus('rejected'),
    }).subscribe({
      next: ({ pending, approved, rejected }) => {
        this.allAudios = [...pending, ...approved, ...rejected].sort((a, b) => {
          const statusOrder = this.statusOrder(a.status) - this.statusOrder(b.status);
          if (statusOrder !== 0) return statusOrder;
          return Date.parse(b.created_at) - Date.parse(a.created_at);
        });
        this.applyClassFilter();
        const requestedAudioId = Number(this.route.snapshot.queryParamMap.get('audioId') || 0);
        const requestedIndex = this.audios.findIndex((audio) => audio.id === requestedAudioId);
        if (requestedIndex >= 0) {
          this.selectedIndex = requestedIndex;
        }
        this.loadExistingComment();
        this.loading = false;
        this.loadPhrase();
        setTimeout(() => this.reloadPlayer());
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Chargement des enregistrements impossible.';
        this.loading = false;
      },
    });
  }

  private statusOrder(status: AudioRead['status']): number {
    if (status === 'pending') return 0;
    if (status === 'approved') return 1;
    return 2;
  }

  private loadPhrase(): void {
    const current = this.current;
    this.currentPhrase = null;
    if (!current) {
      this.cdr.markForCheck();
      return;
    }
    this.api.getPhrase(current.phrase_id).subscribe({
      next: (phrase) => {
        this.currentPhrase = phrase;
        this.cdr.markForCheck();
      },
      error: () => {
        this.currentPhrase = {
          id: current.phrase_id,
          texte: 'Phrase indisponible',
          theme: null,
          niveau: null,
          source: null,
          langue: null,
          auteur: null,
          created_at: '',
        };
        this.cdr.markForCheck();
      },
    });
  }

  private async decide(approved: boolean): Promise<void> {
    const current = this.current;
    if (!current || this.acting) return;
    if (approved && (!this.pronunciationLevel || !this.pronunciationRegion)) {
      this.error = 'Choisissez un niveau et une région de prononciation avant de valider.';
      return;
    }
    this.acting = true;
    this.error = null;
    this.success = null;

    try {
      const profile = this.profileService.profile();
      const updated = await firstValueFrom(approved
        ? this.validations.approve(current.id, {
            validator: this.auth.user()?.display_name || profile.displayName || profile.email || 'Validateur',
            validator_role: this.auth.user()?.role || profile.role,
            validation_weight: this.profileService.validationWeight(profile),
            comment: this.comment.trim() || undefined,
            pronunciation_level: this.pronunciationLevel,
            pronunciation_region: this.pronunciationRegion,
          })
        : this.validations.reject(current.id, {
            validator: this.auth.user()?.display_name || profile.displayName || profile.email || 'Validateur',
            validator_role: this.auth.user()?.role || profile.role,
            validation_weight: this.profileService.validationWeight(profile),
            comment: this.comment.trim() || undefined,
          }),
      );
      this.replaceAudio(updated);
      this.loadExistingComment();
      this.success = approved ? 'Enregistrement valide.' : 'Enregistrement marque a revoir.';
      this.playbackError = null;
      this.loadPhrase();
      setTimeout(() => this.reloadPlayer());
    } catch (err: any) {
      this.error = err?.error?.detail || err?.message || 'Validation impossible pour le moment.';
    } finally {
      this.acting = false;
      this.cdr.markForCheck();
    }
  }

  private reloadPlayer(): void {
    const player = this.playerRef?.nativeElement;
    if (!player) return;
    try {
      player.pause();
      player.currentTime = 0;
      player.load();
    } catch {}
  }

  private get teacherClassNames(): string[] {
    const user = this.auth.user();
    return [user?.school, user?.organization]
      .flatMap((value) => (value || '').split(/[;,]/))
      .map((value) => value.trim())
      .filter((value, index, values) => !!value && values.findIndex((item) => this.canonicalClass(item) === this.canonicalClass(value)) === index);
  }

  private applyClassFilter(resetSelection = true): void {
    const teacherClasses = this.teacherClassNames.map((name) => this.canonicalClass(name));
    this.audios = this.allAudios.filter((audio) => {
      const audioClass = this.canonicalClass(audio.contributor_school || '');
      if (this.isTeacher && teacherClasses.length && !teacherClasses.includes(audioClass)) return false;
      if (this.feedbackView && !this.isTeacher) {
        const userEmail = this.auth.user()?.email?.toLowerCase();
        if (!userEmail || audio.contributor_email?.toLowerCase() !== userEmail) return false;
      }
      return !this.selectedClass || audioClass === this.canonicalClass(this.selectedClass);
    });
    if (resetSelection) this.selectedIndex = 0;
    else if (this.selectedIndex >= this.audios.length) this.selectedIndex = Math.max(0, this.audios.length - 1);
    this.comment = '';
    this.loadPhrase();
    setTimeout(() => this.reloadPlayer());
  }

  private replaceAudio(updated: AudioRead): void {
    this.allAudios = this.allAudios.map((audio) => audio.id === updated.id ? updated : audio);
    this.audios = this.audios.map((audio) => audio.id === updated.id ? updated : audio);
  }

  private loadExistingComment(): void {
    const audio = this.current;
    if (!audio) {
      this.comment = '';
      return;
    }
    const teacherComment = (audio.validations ?? [])
      .find((validation) => validation.comment && (validation.validator_role === 'teacher' || validation.validator_role === 'admin'))
      ?.comment;
    this.comment = teacherComment || audio.validation_comment || '';
    this.pronunciationLevel = (audio.validations ?? [])
      .find((validation) => validation.pronunciation_level)?.pronunciation_level || '';
    this.pronunciationRegion = (audio.validations ?? [])
      .find((validation) => validation.pronunciation_region)?.pronunciation_region || '';
  }

  private canonicalClass(value: string): string {
    return value.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/_/g, '-').replace(/\s+/g, '-');
  }
}
