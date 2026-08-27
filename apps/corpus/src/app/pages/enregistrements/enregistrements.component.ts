import { Component, ChangeDetectionStrategy, ChangeDetectorRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { ValidationsService } from '../../core/validations.service';
import { AudioRead } from '../../core/models';
import { audioFileUrl } from '../../core/constants';
import { DOMAIN_OPTIONS, domainLabelKey } from '../../core/domains';
import { AuthService } from '../../core/auth.service';
import { I18nService } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { SCHOOL_LEVEL_OPTIONS, SCHOOL_OPTIONS } from '../../core/profile.service';

type CorpusStatus = 'all' | 'pending' | 'approved' | 'rejected';

interface CorpusItem {
  audio: AudioRead;
  validationLabel: string;
}

@Component({
  selector: 'app-enregistrements',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './enregistrements.component.html',
  styleUrls: ['./enregistrements.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EnregistrementsComponent implements OnInit {
  loading = false;
  error: string | null = null;

  pending: AudioRead[] = [];
  approved: AudioRead[] = [];
  rejected: AudioRead[] = [];
  statusFilter: CorpusStatus = 'all';
  domainFilter = '';
  levelFilter = '';
  schoolFilter = '';
  schoolLevelFilter = '';
  mineOnly = false;
  readonly domains = DOMAIN_OPTIONS;
  readonly schools = SCHOOL_OPTIONS;
  readonly schoolLevels = SCHOOL_LEVEL_OPTIONS;
  readonly validationLevels = [
    { value: '', labelKey: 'corpus.allLevels' },
    { value: 'approved', labelKey: 'corpus.valid' },
    { value: 'rejected', labelKey: 'corpus.rejectedOne' },
    { value: 'expert', labelKey: 'corpus.qualified' },
  ];

  constructor(
    private readonly svc: ValidationsService,
    private readonly cdr: ChangeDetectorRef,
    readonly auth: AuthService,
    private readonly i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  get items(): CorpusItem[] {
    return [...this.pending, ...this.approved, ...this.rejected]
      .filter((audio) => this.statusFilter === 'all' || audio.status === this.statusFilter)
      .filter((audio) => !this.domainFilter || this.domainValues(audio.domain).includes(this.domainFilter))
      .filter((audio) => !this.schoolFilter || audio.contributor_school === this.schoolFilter)
      .filter((audio) => !this.schoolLevelFilter || audio.contributor_school_level === this.schoolLevelFilter)
      .filter((audio) => !this.mineOnly || this.isMine(audio))
      .filter((audio) => {
        if (!this.levelFilter) return true;
        if (this.levelFilter === 'expert') {
          return this.hasQualifiedValidation(audio);
        }
        return audio.status === this.levelFilter;
      })
      .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
      .map((audio) => ({
        audio,
        validationLabel: this.statusLabel(audio),
      }));
  }

  get canSeeValidationDetails(): boolean {
    const role = this.auth.user()?.role;
    return !!role && ['teacher', 'native', 'senior', 'admin'].includes(role);
  }

  get total(): number {
    return this.pending.length + this.approved.length + this.rejected.length;
  }

  refresh(): void {
    this.loading = true;
    this.error = null;

    forkJoin({
      pending: this.svc.listByStatus('pending'),
      approved: this.svc.listByStatus('approved'),
      rejected: this.svc.listByStatus('rejected'),
    })
    .pipe(finalize(() => { this.loading = false; this.cdr.markForCheck(); }))
    .subscribe({
      next: ({ pending, approved, rejected }) => {
        this.pending = pending || [];
        this.approved = approved || [];
        this.rejected = rejected || [];
      },
      error: (e) => {
        this.error = e?.message ?? 'Loading error';
      }
    });
  }

  url(a: AudioRead): string {
    return audioFileUrl(a.id);
  }

  domainLabel(value?: string | null): string {
    const values = this.domainValues(value);
    if (!values.length) return this.i18n.translate(domainLabelKey(value));
    return values.map((item) => this.i18n.translate(domainLabelKey(item))).join(', ');
  }

  schoolLabel(value?: string | null): string {
    const option = this.schools.find((item) => item.value === (value ?? ''));
    return option ? this.i18n.translate(option.labelKey) : value ?? '';
  }

  schoolLevelLabel(value?: string | null): string {
    const option = this.schoolLevels.find((item) => item.value === (value ?? ''));
    return option ? this.i18n.translate(option.labelKey) : value ?? '';
  }

  validations(audio: AudioRead) {
    const items = audio.validations || [];
    if (items.length) return items;
    if (!audio.validated_by && !audio.validated_at) return [];
    return [{
      id: 0,
      audio_id: audio.id,
      decision: audio.status,
      validator: audio.validated_by,
      validator_role: audio.validator_role,
      validation_weight: audio.validation_weight,
      comment: audio.validation_comment,
      created_at: audio.validated_at || audio.created_at,
    }];
  }

  latestComment(audio: AudioRead): string | null {
    const validation = this.validations(audio).find((item) => !!item.comment);
    return validation?.comment || audio.validation_comment || null;
  }

  validationSummary(audio: AudioRead): string {
    const validations = this.validations(audio);
    const yes = validations.filter((item) => item.decision === 'approved').length;
    const no = validations.filter((item) => item.decision === 'rejected').length;
    if (!validations.length) return this.i18n.translate('corpus.summaryNone');
    return `${validations.length} ${this.i18n.translate('corpus.summary')} : ${yes} ${this.i18n.translate('corpus.yes')} / ${no} ${this.i18n.translate('corpus.no')}`;
  }

  private hasQualifiedValidation(audio: AudioRead): boolean {
    return this.validations(audio).some((item) => {
      const role = item.validator_role || '';
      return ['teacher', 'native', 'senior', 'admin'].includes(role);
    });
  }

  private isMine(audio: AudioRead): boolean {
    const user = this.auth.user();
    if (!user) return false;
    return audio.contributor_email === user.email
      || audio.contributor_name === user.display_name;
  }

  private statusLabel(audio: AudioRead): string {
    if (audio.status === 'pending') return this.i18n.translate('corpus.pendingOne');
    if (audio.status === 'approved') return this.i18n.translate('corpus.valid');
    return this.i18n.translate('corpus.rejectedOne');
  }

  private domainValues(value?: string | null): string[] {
    return (value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  trackById(_i: number, item: CorpusItem) { return item.audio.id; }
}
