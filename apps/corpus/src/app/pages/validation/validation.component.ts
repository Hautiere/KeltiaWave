// path: frontend/src/app/pages/validation/validation.component.ts
import { Component, OnInit, HostListener, ChangeDetectionStrategy, ChangeDetectorRef, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom, forkJoin } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { ValidationsService } from '../../core/validations.service';
import { ApiService } from '../../core/api.service';
import { AudioRead } from '../../core/models';
import { audioFileUrl } from '../../core/constants';
import { TranslatePipe } from '../../core/translate.pipe';
import { DOMAIN_OPTIONS } from '../../core/domains';
import { ProfileService } from '../../core/profile.service';
import { I18nService } from '../../core/i18n.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-validation',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './validation.component.html',
  styleUrls: ['./validation.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ValidationComponent implements OnInit {
  // Listes
  audios: AudioRead[] = [];            // pending
  approvedList: AudioRead[] = [];
  rejectedList: AudioRead[] = [];

  // Sélection dans pending
  selectedIndex = 0;

  // États UI
  loading = false;
  acting  = false;
  error: string | null = null;
  statusMsg: string | null = null;
  validationComment = '';
  selectedApproveReasons: string[] = [];
  selectedRejectReasons: string[] = [];
  approveMode = false;
  rejectMode = false;
  savingMeta = false;
  metadata = {
    phrase_source: '',
    domain: '',
    speaker_region: '',
    speaker_city: '',
    speaker_accent: '',
    speaker_level: '',
  };
  readonly domains = DOMAIN_OPTIONS;
  readonly rejectReasons = [
    { value: 'accentuation', labelKey: 'validation.reasonStress' },
    { value: 'rythme', labelKey: 'validation.reasonRhythm' },
    { value: 'prononciation', labelKey: 'validation.reasonPronunciation' },
    { value: 'intonation', labelKey: 'validation.reasonIntonation' },
    { value: 'fluidite', labelKey: 'validation.reasonFluency' },
    { value: 'texte-lu', labelKey: 'validation.reasonText' },
    { value: 'qualite-audio', labelKey: 'validation.reasonAudio' },
    { value: 'non-breton', labelKey: 'validation.reasonLanguage' },
  ];
  readonly approveReasons = [
    { value: 'prononciation-claire', labelKey: 'validation.goodPronunciation' },
    { value: 'rythme-naturel', labelKey: 'validation.goodRhythm' },
    { value: 'accentuation-naturelle', labelKey: 'validation.goodStress' },
    { value: 'intonation-naturelle', labelKey: 'validation.goodIntonation' },
    { value: 'fluide', labelKey: 'validation.goodFluency' },
    { value: 'texte-conforme', labelKey: 'validation.goodText' },
    { value: 'audio-propre', labelKey: 'validation.goodAudio' },
    { value: 'breton-naturel', labelKey: 'validation.goodBreton' },
  ];
  readonly regions = [
    { value: '', label: 'Not specified' },
    { value: 'bro-dreger', label: 'Bro Dreger' },
    { value: 'bro-leon', label: 'Bro Leon' },
    { value: 'bro-gernev', label: 'Bro Gernev' },
    { value: 'bro-wened', label: 'Bro Gwened' },
    { value: 'bro-saint-brieuc', label: 'Bro Sant-Brieg' },
    { value: 'other', label: 'Other / not sure' },
  ];
  readonly accents = [
    { value: '', label: 'Not specified' },
    { value: 'tregerieg', label: 'Tregerieg / Tregor' },
    { value: 'leoneg', label: 'Leoneg / Leon' },
    { value: 'kerneveg', label: 'Kerneveg / Cornouaille' },
    { value: 'gwenedeg', label: 'Gwenedeg / Vannes' },
    { value: 'mixed', label: 'Mixed / hard to classify' },
    { value: 'non-native', label: 'Non-native accent' },
  ];
  readonly levels = [
    { value: '', labelKey: 'level.undefined' },
    { value: 'A1', labelKey: 'level.A1' },
    { value: 'A2', labelKey: 'level.A2' },
    { value: 'B1', labelKey: 'level.B1' },
    { value: 'B2', labelKey: 'level.B2' },
    { value: 'C1', labelKey: 'level.C1' },
    { value: 'C2', labelKey: 'level.C2' },
    { value: 'native-heritage', labelKey: 'level.nativeHeritage' },
    { value: 'not-sure', labelKey: 'level.notSure' },
  ];

  // Texte phrase courante (pending)
  phraseText: string | null = null;
  private lastPhraseId: number | null = null;

  // 🔒 Switch anti-régression : mets false pour revenir à "pending only"
  readonly SHOW_HISTORY = true;

  // Référence lecteur + helper de reload
  @ViewChild('player') private playerRef?: ElementRef<HTMLAudioElement>;
  private reloadPlayer(): void {
    const el = this.playerRef?.nativeElement;
    if (!el) return;
    try {
      el.pause();
      el.currentTime = 0;
      el.load(); // force le rechargement de la nouvelle source
    } catch {}
  }

  constructor(
    private readonly svc: ValidationsService,
    private readonly api: ApiService,
    readonly profileService: ProfileService,
    private readonly auth: AuthService,
    private readonly i18n: I18nService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  get isDragonTheme(): boolean {
    return false;
  }

  get isBlueTriskell(): boolean {
    const language = this.i18n.language();
    return language === 'en' || language === 'cy';
  }

  ngOnInit(): void { this.refresh(); }

  refresh(): void {
    this.loading = true; this.error = null;

    const load$ = this.SHOW_HISTORY
      ? forkJoin({
          pending:  this.svc.listByStatus('pending'),
          approved: this.svc.listByStatus('approved'),
          rejected: this.svc.listByStatus('rejected'),
        })
      : forkJoin({
          pending:  this.svc.listByStatus('pending'),
          approved: [], rejected: [],
        } as any);

    load$
    .pipe(finalize(() => { this.loading = false; this.cdr.markForCheck(); }))
    .subscribe({
      next: ({ pending, approved, rejected }: any) => {
        const pendingItems = Array.isArray(pending) ? pending : [];
        this.approvedList = Array.isArray(approved) ? approved : [];
        this.rejectedList = Array.isArray(rejected) ? rejected : [];
        this.audios = [
          ...pendingItems,
          ...this.approvedList,
          ...this.rejectedList,
        ].sort((a, b) => {
          if (a.status === 'pending' && b.status !== 'pending') return -1;
          if (a.status !== 'pending' && b.status === 'pending') return 1;
          return Date.parse(b.created_at) - Date.parse(a.created_at);
        });
        this.selectedIndex = 0;
        this.lastPhraseId = null;
        this.syncMetadataFromCurrent();
        this.loadPhrase();
        setTimeout(() => this.reloadPlayer());
      },
      error: (err: unknown) => {
        this.error = err instanceof Error ? err.message : String(err);
      }
    });
  }

  get current(): AudioRead | null {
    return this.audios[this.selectedIndex] ?? null;
  }

  url(a: AudioRead | null): string {
    return a ? audioFileUrl(a.id) : '';
  }

  playCurrent(): void {
    const el = this.playerRef?.nativeElement;
    if (!el) return;
    try {
      if (!el.paused) {
        el.pause();
        return;
      }
      void el.play();
    } catch {}
  }

  select(i: number): void {
    if (this.acting) return;
    this.selectedIndex = i;
    this.syncMetadataFromCurrent();
    this.loadPhrase();
    this.cdr.markForCheck();
    setTimeout(() => this.reloadPlayer());
  }

  approve(): void {
    if (this.acting) return;
    this.approveMode = true;
    this.rejectMode = false;
    this.cdr.markForCheck();
  }

  reject(): void {
    if (this.acting) return;
    this.approveMode = false;
    this.rejectMode = true;
    this.cdr.markForCheck();
  }

  confirmApprove(): void {
    this.approveMode = false;
    void this.decide(true);
  }

  confirmReject(): void {
    this.rejectMode = false;
    void this.decide(false);
  }

  cancelReject(): void {
    this.rejectMode = false;
    this.validationComment = '';
    this.selectedRejectReasons = [];
    this.cdr.markForCheck();
  }

  cancelApprove(): void {
    this.approveMode = false;
    this.validationComment = '';
    this.selectedApproveReasons = [];
    this.cdr.markForCheck();
  }

  toggleApproveReason(reason: string): void {
    this.selectedApproveReasons = this.selectedApproveReasons.includes(reason)
      ? this.selectedApproveReasons.filter((item) => item !== reason)
      : [...this.selectedApproveReasons, reason];
    this.cdr.markForCheck();
  }

  toggleRejectReason(reason: string): void {
    this.selectedRejectReasons = this.selectedRejectReasons.includes(reason)
      ? this.selectedRejectReasons.filter((item) => item !== reason)
      : [...this.selectedRejectReasons, reason];
    this.cdr.markForCheck();
  }

  private async decide(approved: boolean): Promise<void> {
    const cur = this.current; if (!cur || this.acting) return;

    this.acting = true;
    const prevPending = [...this.audios];

    try {
      const saved = await this.saveMetadata(false);
      const audioForMove = saved ?? { ...cur, ...this.metadataPayload() };

      this.audios = prevPending.filter(x => x.id !== cur.id);
      this.cdr.markForCheck();

      const validatorProfile = this.validatorProfilePayload();
      await firstValueFrom(approved ? this.svc.approve(cur.id, validatorProfile) : this.svc.reject(cur.id, validatorProfile));

      if (this.selectedIndex >= this.audios.length) {
        this.selectedIndex = Math.max(0, this.audios.length - 1);
      }
      const moved: AudioRead = {
        ...audioForMove,
        status: approved ? 'approved' : 'rejected',
        validated_at: new Date().toISOString(),
        validated_by: validatorProfile.validator ?? null,
        validator_role: validatorProfile.validator_role ?? null,
        validation_weight: String(validatorProfile.validation_weight ?? ''),
        validation_comment: validatorProfile.comment ?? null,
      } as AudioRead;

      if (this.SHOW_HISTORY) {
        this.approvedList = this.approvedList.filter((audio) => audio.id !== cur.id);
        this.rejectedList = this.rejectedList.filter((audio) => audio.id !== cur.id);
        if (approved) this.approvedList = [moved, ...this.approvedList];
        else          this.rejectedList = [moved, ...this.rejectedList];
      }

      this.lastPhraseId = null;
      this.syncMetadataFromCurrent();
      this.loadPhrase();
      setTimeout(() => this.reloadPlayer());
      this.showMsg(approved ? 'Approved' : 'Rejected');
    } catch (err: unknown) {
      this.error = err instanceof Error ? err.message : String(err);
      this.audios = prevPending;
    } finally {
      this.acting = false;
      this.cdr.markForCheck();
    }
  }

  next(): void {
    if (!this.audios.length || this.acting) return;
    this.approveMode = false;
    this.rejectMode = false;
    this.validationComment = '';
    this.selectedApproveReasons = [];
    this.selectedRejectReasons = [];
    this.selectedIndex = (this.selectedIndex + 1) % this.audios.length;
    this.syncMetadataFromCurrent();
    this.loadPhrase();
    this.cdr.markForCheck();
    setTimeout(() => this.reloadPlayer());
  }

  private loadPhrase(): void {
    const cur = this.current;
    if (!cur) { this.phraseText = null; this.lastPhraseId = null; return; }
    if (this.lastPhraseId === cur.phrase_id) return;

    this.lastPhraseId = cur.phrase_id;
    this.api.getPhrase(cur.phrase_id).subscribe({
      next: (p: any) => { this.phraseText = p?.texte ?? '(text unavailable)'; this.cdr.markForCheck(); },
      error: () => { this.phraseText = '(text unavailable)'; this.cdr.markForCheck(); }
    });
  }

  private showMsg(txt: string) {
    this.statusMsg = txt;
    setTimeout(() => { this.statusMsg = null; this.cdr.markForCheck(); }, 1500);
  }

  trackById(_i: number, a: AudioRead) { return a.id; }

  async saveMetadata(showMessage = true): Promise<AudioRead | null> {
    const cur = this.current;
    if (!cur || this.savingMeta) return null;

    this.savingMeta = true;
    this.error = null;
    this.cdr.markForCheck();
    try {
      const updated = await firstValueFrom(this.svc.updateMetadata(cur.id, this.metadataPayload()));
      this.audios = this.audios.map((audio) => audio.id === updated.id ? updated : audio);
      if (showMessage) this.showMsg('Metadata saved');
      return updated;
    } catch (err: unknown) {
      this.error = err instanceof Error ? err.message : String(err);
      throw err;
    } finally {
      this.savingMeta = false;
      this.cdr.markForCheck();
    }
  }

  private metadataPayload() {
    return {
      phrase_source: this.metadata.phrase_source,
      domain: this.metadata.domain,
      speaker_region: this.metadata.speaker_region,
      speaker_city: this.metadata.speaker_city.trim(),
      speaker_accent: this.metadata.speaker_accent,
      speaker_level: this.metadata.speaker_level,
    };
  }

  private validatorProfilePayload() {
    const profile = this.profileService.profile();
    if (!this.auth.user()) {
      return {
        validator: 'Visiteur',
        validator_role: 'anonymous_reviewer',
        validation_weight: this.profileService.validationWeight(profile),
        comment: this.validationCommentPayload(),
      };
    }
    return {
      validator: profile.displayName || profile.email || 'Anonyme',
      validator_role: profile.role,
      validation_weight: this.profileService.validationWeight(profile),
      comment: this.validationCommentPayload(),
    };
  }

  private validationCommentPayload(): string {
    const comment = this.validationComment.trim();
    const reasons = [
      ...this.selectedApproveReasons,
      ...this.selectedRejectReasons,
    ].join(', ');
    if (reasons && comment) return `${reasons} - ${comment}`;
    return reasons || comment;
  }

  private syncMetadataFromCurrent(): void {
    const cur = this.current;
    this.metadata = {
      phrase_source: cur?.phrase_source ?? '',
      domain: cur?.domain ?? '',
      speaker_region: cur?.speaker_region ?? '',
      speaker_city: cur?.speaker_city ?? '',
      speaker_accent: cur?.speaker_accent ?? '',
      speaker_level: cur?.speaker_level ?? '',
    };
    this.validationComment = '';
    this.selectedApproveReasons = [];
    this.selectedRejectReasons = [];
    this.approveMode = false;
    this.rejectMode = false;
  }

  @HostListener('window:keydown', ['$event'])
  onKey(e: KeyboardEvent): void {
    if (this.loading || this.acting) return;
    const target = e.target as HTMLElement | null;
    if (target?.closest('input, textarea, select, button')) return;
    const k = e.key.toLowerCase();
    if (k === 'a') this.approve();
    if (k === 'r') this.reject();
    if (k === 'n') this.next();
    if (k === ' ') {
      e.preventDefault();
      this.playCurrent();
    }
  }
}
