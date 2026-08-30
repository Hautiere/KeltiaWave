import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService, AudioRead, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { audioFileUrl } from '../../core/constants';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

interface AudioRow {
  audio: AudioRead;
  phrase: Phrase | null;
}

interface ThemeFilter {
  value: string;
  labelKey: string;
  icon: string;
  tone: string;
}

interface LibraryFilterOption {
  value: string;
  labelKey: string;
  icon: string;
}

@Component({
  selector: 'app-v2-audio-home',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-audio-home.component.html',
  styleUrls: ['./v2-audio-home.component.scss'],
})
export class V2AudioHomeComponent implements OnInit {
  @ViewChild('libraryPlayer') private libraryPlayer?: ElementRef<HTMLAudioElement>;

  phrases: Phrase[] = [];
  fallbackPhrases: Phrase[] = [];
  approvedAudios: AudioRead[] = [];
  pendingAudios: AudioRead[] = [];
  rejectedAudios: AudioRead[] = [];
  loading = true;
  error: string | null = null;
  query = '';
  selectedTheme = '';
  selectedLevel = '';
  selectedDuration = '';
  selectedSource = '';
  selectedValidation = '';
  selectedRegion = '';
  showAllThemes = false;
  visibleThemeLimit = 7;
  activeAudioId: number | null = null;
  isPlayingAudio = false;
  playbackError: string | null = null;
  librarySort: 'phrase' | 'theme' | 'level' | 'region' | 'date' = 'date';
  librarySortDirection: 'asc' | 'desc' = 'desc';

  readonly waveformBars = [
    12, 20, 30, 16, 22, 14, 28, 36, 18, 12, 24, 16, 10, 20, 14, 8, 18, 12,
  ];

  readonly themes: ThemeFilter[] = [
    { value: '', labelKey: 'v2.allThemes', icon: '♪', tone: 'blue' },
    { value: 'vie-quotidienne', labelKey: 'domain.dailyLife', icon: '☕', tone: 'green' },
    { value: 'education', labelKey: 'domain.education', icon: '◈', tone: 'purple' },
    { value: 'transports', labelKey: 'domain.transport', icon: '▣', tone: 'sky' },
    { value: 'famille', labelKey: 'domain.family', icon: '●●', tone: 'orange' },
    { value: 'travail', labelKey: 'domain.work', icon: '▤', tone: 'brown' },
    { value: 'nature', labelKey: 'domain.nature', icon: '◒', tone: 'leaf' },
    { value: 'sante', labelKey: 'domain.health', icon: '♧', tone: 'red' },
    { value: 'culture-patrimoine', labelKey: 'domain.culture', icon: '◇', tone: 'gold' },
    { value: 'histoire', labelKey: 'domain.history', icon: '▥', tone: 'amber' },
    { value: 'cuisine', labelKey: 'domain.cooking', icon: '◌', tone: 'rose' },
    { value: 'sports-loisirs', labelKey: 'domain.sports', icon: '◎', tone: 'lime' },
    { value: 'technologies', labelKey: 'domain.technology', icon: '⌘', tone: 'indigo' },
    { value: 'administration', labelKey: 'domain.administration', icon: '⌂', tone: 'slate' },
  ];

  readonly sourceFilters: LibraryFilterOption[] = [
    { value: '', labelKey: 'v2.allSources', icon: '◎' },
    { value: 'creation-originale', labelKey: 'source.original', icon: '▤' },
    { value: 'livre', labelKey: 'source.book', icon: '▥' },
    { value: 'dictionnaire', labelKey: 'source.dictionary', icon: '▥' },
    { value: 'cours-breton', labelKey: 'source.course', icon: '◈' },
    { value: 'presse-media', labelKey: 'source.media', icon: '▦' },
    { value: 'archives', labelKey: 'source.archives', icon: '▣' },
    { value: 'conversation', labelKey: 'source.conversation', icon: '♬' },
  ];

  readonly validationFilters: LibraryFilterOption[] = [
    { value: '', labelKey: 'v2.allValidations', icon: '◎' },
    { value: 'A1', labelKey: 'A1', icon: '1' },
    { value: 'A2', labelKey: 'A2', icon: '2' },
    { value: 'B1', labelKey: 'B1', icon: '3' },
    { value: 'B2', labelKey: 'B2', icon: '4' },
    { value: 'C1', labelKey: 'C1', icon: '5' },
    { value: 'C2', labelKey: 'C2', icon: '6' },
    { value: 'native', labelKey: 'Natif', icon: '★' },
  ];

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
  ) {}

  ngOnInit(): void {
    this.updateThemeLimit();
    this.load();
  }

  get corpusRows(): AudioRow[] {
    return this.sortLibraryRows(this.filterRows(
      this.toRows(this.approvedAudios).filter(({ audio }) => this.teacherDecision(audio) === 'approved'),
    ));
  }

  sortLibraryBy(column: 'phrase' | 'theme' | 'level' | 'region' | 'date'): void {
    if (this.librarySort === column) {
      this.librarySortDirection = this.librarySortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.librarySort = column;
    this.librarySortDirection = 'asc';
  }

  librarySortIndicator(column: 'phrase' | 'theme' | 'level' | 'region' | 'date'): string {
    return this.librarySort === column ? (this.librarySortDirection === 'asc' ? '▲' : '▼') : '△';
  }

  get myRows(): AudioRow[] {
    const email = this.auth.user()?.email?.toLowerCase();
    if (!email) return [];
    return this.filterRows(
      this.toRows([...this.pendingAudios, ...this.approvedAudios, ...this.rejectedAudios])
        .filter(({ audio }) => audio.contributor_email?.toLowerCase() === email),
    );
  }

  get myRowsStateMessage(): string {
    if (this.loading) return this.i18n.translate('corpus.loading');
    if (!this.auth.user()) return this.i18n.translate('v2.classNotConnected');
    return this.i18n.translate('v2.noMyPhrases');
  }

  get classRows(): AudioRow[] {
    const user = this.auth.user();
    if (!user || !this.hasClassContext) return [];
    const userEmail = user?.email?.toLowerCase();
    const userSchool = this.canonicalClassValue(user?.school || user?.organization);
    const userSchoolLevel = this.canonicalSchoolLevel(user?.school_level || this.schoolLevelFromEmail(user?.email));
    const mine = this.toRows([...this.pendingAudios, ...this.approvedAudios]).filter(({ audio }) => {
      const emailMatch = !!userEmail && audio.contributor_email?.toLowerCase() === userEmail;
      const audioSchool = this.canonicalClassValue(audio.contributor_school);
      const audioSchoolLevel = this.canonicalSchoolLevel(audio.contributor_school_level);
      const schoolMatch = !!userSchool && audioSchool === userSchool;
      const levelMatch = !userSchoolLevel || !audioSchoolLevel || audioSchoolLevel === userSchoolLevel;
      return emailMatch || (schoolMatch && levelMatch);
    });
    return this.filterRows(mine).slice(0, 6);
  }

  get hasClassContext(): boolean {
    const user = this.auth.user();
    return !!this.canonicalClassValue(user?.school || user?.organization);
  }

  get classStateMessage(): string {
    if (this.loading) return this.i18n.translate('corpus.loading');
    if (!this.auth.user()) return this.i18n.translate('v2.classNotConnected');
    if (!this.hasClassContext) return this.i18n.translate('v2.classNotMember');
    return this.i18n.translate('v2.noClassRecordings');
  }

  get visibleThemes(): ThemeFilter[] {
    return this.themes.slice(0, this.visibleThemeLimit);
  }

  get hiddenThemes(): ThemeFilter[] {
    return this.themes.slice(this.visibleThemeLimit);
  }

  get levelOptions(): string[] {
    return this.uniqueValues(this.allRows().map((row) => row.phrase?.niveau || row.audio.speaker_level));
  }

  get validationRegionOptions(): string[] {
    return this.uniqueValues(this.approvedAudios.flatMap((audio) =>
      (audio.validations ?? [])
        .filter((validation) => validation.decision === 'approved' && (validation.validator_role === 'teacher' || validation.validator_role === 'admin'))
        .map((validation) => validation.pronunciation_region),
    ));
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      this.load();
    }
  }

  selectTheme(value: string): void {
    this.selectedTheme = value;
    this.showAllThemes = false;
  }

  resetFilters(): void {
    this.query = '';
    this.selectedTheme = '';
    this.selectedLevel = '';
    this.selectedDuration = '';
    this.selectedSource = '';
    this.selectedValidation = '';
    this.selectedRegion = '';
  }

  phraseText(row: AudioRow): string {
    return this.resolvePhrase(row)?.texte || 'Enregistrement sans texte associé';
  }

  phrasePreview(row: AudioRow): string {
    const text = this.phraseText(row).trim();
    const words = text.split(/\s+/).filter(Boolean);
    if (words.length <= 7) return text;
    return `${words.slice(0, 7).join(' ')}...`;
  }

  themeLabel(value?: string | null): string {
    if (!value) return this.i18n.translate('v2.noTheme');
    const first = value.split(',')[0]?.trim();
    const canonical = this.canonicalTheme(first);
    const theme = this.themes.find((item) => item.value === canonical);
    return theme ? this.i18n.translate(theme.labelKey) : first || value;
  }

  filterLabel(option: LibraryFilterOption): string {
    return this.i18n.translate(option.labelKey);
  }

  themeFilterLabel(theme: ThemeFilter): string {
    return this.i18n.translate(theme.labelKey);
  }

  validationSummary(audio: AudioRead): string {
    const validations = audio.validations ?? [];
    const approved = validations.length
      ? validations.filter((validation) => validation.decision === 'approved').length
      : (audio.status === 'approved' ? 1 : 0);
    const rejected = validations.length
      ? validations.filter((validation) => validation.decision === 'rejected').length
      : (audio.status === 'rejected' ? 1 : 0);
    if (!approved && !rejected) return this.i18n.translate('corpus.summaryNone');
    return `${approved} ${this.i18n.translate('v2.validationApprovals')} · ${rejected} ${this.i18n.translate('v2.validationRejections')}`;
  }

  teacherComment(audio: AudioRead): string | null {
    const validation = (audio.validations ?? [])
      .find((item) => item.comment && (item.validator_role === 'teacher' || item.validator_role === 'admin'));
    return validation?.comment || (audio.validator_role === 'teacher' || audio.validator_role === 'admin' ? audio.validation_comment || null : null);
  }

  teacherDecision(audio: AudioRead): 'approved' | 'rejected' | 'pending' {
    const validation = (audio.validations ?? [])
      .find((item) => (item.validator_role === 'teacher' || item.validator_role === 'admin') && (item.decision === 'approved' || item.decision === 'rejected'));
    if (validation?.decision === 'approved' || validation?.decision === 'rejected') return validation.decision;
    if ((audio.validator_role === 'teacher' || audio.validator_role === 'admin') && (audio.status === 'approved' || audio.status === 'rejected')) return audio.status;
    return 'pending';
  }

  teacherDecisionLabel(audio: AudioRead): string {
    const decision = this.teacherDecision(audio);
    if (decision === 'approved') return 'Validé par le professeur';
    if (decision === 'rejected') return 'À revoir';
    return 'En attente du professeur';
  }

  pronunciationLevel(audio: AudioRead): string {
    const level = (audio.validations ?? [])
      .find((item) => (item.validator_role === 'teacher' || item.validator_role === 'admin') && item.decision === 'approved')
      ?.pronunciation_level;
    return level === 'native' ? 'Natif' : level || 'NA';
  }

  pronunciationRegion(audio: AudioRead): string {
    return (audio.validations ?? [])
      .find((item) => (item.validator_role === 'teacher' || item.validator_role === 'admin') && item.decision === 'approved')
      ?.pronunciation_region || 'Région non renseignée';
  }

  sourceUrl(row: AudioRow): string | null {
    return row.phrase?.source_url || null;
  }

  sourceLabel(row: AudioRow): string {
    const sourceUrl = this.sourceUrl(row);
    if (!sourceUrl) return '—';
    try {
      return new URL(sourceUrl).hostname.replace(/^www\./, '');
    } catch {
      return 'Source';
    }
  }

  themeTone(value?: string | null): string {
    const first = value?.split(',')[0]?.trim() || '';
    return this.themes.find((theme) => theme.value === this.canonicalTheme(first))?.tone || 'blue';
  }

  themeIcon(value?: string | null): string {
    const first = value?.split(',')[0]?.trim() || '';
    return this.themes.find((theme) => theme.value === this.canonicalTheme(first))?.icon || '♪';
  }

  themeClass(value?: string | null): string {
    return `theme-glyph ${this.themeTone(value)}`;
  }

  audioUrl(audio: AudioRead): string {
    return audioFileUrl(audio.id);
  }

  toggleAudio(row: AudioRow): void {
    const player = this.libraryPlayer?.nativeElement;
    if (!player) return;

    this.playbackError = null;
    if (this.activeAudioId === row.audio.id && this.isPlayingAudio) {
      player.pause();
      this.isPlayingAudio = false;
      return;
    }

    this.activeAudioId = row.audio.id;
    player.src = this.audioUrl(row.audio);
    player.load();
    player.play()
      .then(() => {
        this.isPlayingAudio = true;
      })
      .catch(() => {
        this.isPlayingAudio = false;
        this.playbackError = this.i18n.translate('v2.audioPlaybackError');
      });
  }

  isRowPlaying(row: AudioRow): boolean {
    return this.activeAudioId === row.audio.id && this.isPlayingAudio;
  }

  onPlaybackEnded(): void {
    this.activeAudioId = null;
    this.isPlayingAudio = false;
  }

  onPlaybackPaused(): void {
    this.isPlayingAudio = false;
  }

  onPlaybackError(): void {
    this.isPlayingAudio = false;
    this.playbackError = this.i18n.translate('v2.audioPlaybackError');
  }

  displayDate(value: string): string {
    const locale = this.i18n.language() === 'fr' ? 'fr-FR' : this.i18n.language() === 'br' ? 'br-FR' : this.i18n.language() === 'cy' ? 'cy-GB' : 'en-GB';
    return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
  }

  durationLabel(): string {
    return '--:--';
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    this.updateThemeLimit();
  }

  private load(): void {
    this.loading = true;
    this.error = null;
    forkJoin({
      phrases: this.api.getPhrases(this.i18n.contentLanguage()),
      fallbackPhrases: this.api.getPhrases(),
      approved: this.api.listAudios('approved'),
      pending: this.api.listAudios('pending'),
      rejected: this.api.listAudios('rejected'),
    }).subscribe({
      next: ({ phrases, fallbackPhrases, approved, pending, rejected }) => {
        this.phrases = phrases;
        this.fallbackPhrases = fallbackPhrases;
        this.approvedAudios = approved;
        this.pendingAudios = pending;
        this.rejectedAudios = rejected;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Chargement impossible.';
        this.loading = false;
      },
    });
  }

  private toRows(audios: AudioRead[]): AudioRow[] {
    const phraseById = new Map([
      ...this.fallbackPhrases.map((phrase) => [phrase.id, phrase] as const),
      ...this.phrases.map((phrase) => [phrase.id, phrase] as const),
    ]);
    return audios
      .map((audio) => ({ audio, phrase: phraseById.get(audio.phrase_id) ?? null }))
      .sort((a, b) => b.audio.created_at.localeCompare(a.audio.created_at));
  }

  private resolvePhrase(row: AudioRow): Phrase | null {
    if (row.phrase) return row.phrase;
    return this.fallbackPhrases.find((phrase) => phrase.id === row.audio.phrase_id) ?? null;
  }

  private filterRows(rows: AudioRow[]): AudioRow[] {
    const query = this.query.trim().toLowerCase();
    return rows.filter((row) => {
      const theme = row.phrase?.theme || row.audio.domain || '';
      const rowThemes = theme.split(',').map((item) => this.canonicalTheme(item));
      const matchesTheme = !this.selectedTheme || rowThemes.includes(this.selectedTheme);
      const level = row.phrase?.niveau || row.audio.speaker_level || '';
      const matchesLevel = !this.selectedLevel || level === this.selectedLevel;
      const duration = this.durationCategory(row);
      const matchesDuration = !this.selectedDuration || duration === 'unknown' || duration === this.selectedDuration;
      const matchesSource = !this.selectedSource || this.sourceKeys(row).includes(this.selectedSource);
      const matchesValidation = !this.selectedValidation || this.matchesValidation(row, this.selectedValidation);
      const matchesRegion = !this.selectedRegion || this.pronunciationRegion(row.audio) === this.selectedRegion;
      const haystack = [
        this.phraseText(row),
        row.phrase?.traduction_fr,
        theme,
        level,
        row.phrase?.source,
        row.audio.phrase_source,
        row.audio.contributor_name,
        row.audio.contributor_email,
        row.audio.contributor_school,
        row.audio.speaker_region,
        row.audio.speaker_city,
      ].join(' ').toLowerCase();
      return matchesTheme && matchesLevel && matchesDuration && matchesSource && matchesValidation && matchesRegion && (!query || haystack.includes(query));
    });
  }

  private sortLibraryRows(rows: AudioRow[]): AudioRow[] {
    return [...rows].sort((a, b) => {
      let left = '';
      let right = '';
      if (this.librarySort === 'phrase') {
        left = this.phraseText(a); right = this.phraseText(b);
      } else if (this.librarySort === 'theme') {
        left = this.themeLabel(a.phrase?.theme || a.audio.domain); right = this.themeLabel(b.phrase?.theme || b.audio.domain);
      } else if (this.librarySort === 'level') {
        left = this.pronunciationLevel(a.audio); right = this.pronunciationLevel(b.audio);
      } else if (this.librarySort === 'region') {
        left = this.pronunciationRegion(a.audio); right = this.pronunciationRegion(b.audio);
      } else {
        left = a.audio.created_at; right = b.audio.created_at;
      }
      const comparison = left.localeCompare(right, 'fr');
      return this.librarySortDirection === 'asc' ? comparison : -comparison;
    });
  }

  private allRows(): AudioRow[] {
    return this.toRows([...this.approvedAudios, ...this.pendingAudios, ...this.rejectedAudios]);
  }

  private uniqueValues(values: Array<string | null | undefined>): string[] {
    return [...new Set(values.map((value) => value?.trim()).filter((value): value is string => !!value))].sort((a, b) => a.localeCompare(b));
  }

  private durationCategory(_row: AudioRow): 'short' | 'medium' | 'long' | 'unknown' {
    return 'unknown';
  }

  private sourceKeys(row: AudioRow): string[] {
    return [
      row.phrase?.source,
      row.audio.phrase_source,
    ].map((value) => this.canonicalSource(value)).filter(Boolean);
  }

  private matchesValidation(row: AudioRow, value: string): boolean {
    return (row.audio.validations ?? []).some((validation) =>
      (validation.validator_role === 'teacher' || validation.validator_role === 'admin')
      && validation.decision === 'approved'
      && validation.pronunciation_level === value,
    );
  }

  private updateThemeLimit(): void {
    const width = typeof window === 'undefined' ? 1440 : window.innerWidth;
    if (width >= 1720) {
      this.visibleThemeLimit = 7;
    } else if (width >= 1450) {
      this.visibleThemeLimit = 6;
    } else if (width >= 1180) {
      this.visibleThemeLimit = 5;
    } else if (width >= 860) {
      this.visibleThemeLimit = 4;
    } else {
      this.visibleThemeLimit = 3;
    }
    if (!this.hiddenThemes.length) this.showAllThemes = false;
  }

  private canonicalTheme(value?: string | null): string {
    const normalized = (value ?? '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/&/g, 'et')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const aliases: Record<string, string> = {
      quotidien: 'vie-quotidienne',
      'vie-quotidienne': 'vie-quotidienne',
      daily: 'vie-quotidienne',
      'daily-life': 'vie-quotidienne',
      ecole: 'education',
      'ecole-et-formation': 'education',
      'ecole-formation': 'education',
      education: 'education',
      transports: 'transports',
      transport: 'transports',
      famille: 'famille',
      travail: 'travail',
      nature: 'nature',
      'nature-et-environnement': 'nature',
      'nature-environnement': 'nature',
      sante: 'sante',
      culture: 'culture-patrimoine',
      patrimoine: 'culture-patrimoine',
      'culture-patrimoine': 'culture-patrimoine',
      histoire: 'histoire',
      cuisine: 'cuisine',
      'sports-loisirs': 'sports-loisirs',
      sport: 'sports-loisirs',
      sports: 'sports-loisirs',
      technologie: 'technologies',
      technologies: 'technologies',
      'technologie-medias': 'technologies',
      administration: 'administration',
    };
    return aliases[normalized] || normalized;
  }

  private canonicalSource(value?: string | null): string {
    const normalized = (value ?? '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/&/g, 'et')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const aliases: Record<string, string> = {
      original: 'creation-originale',
      'creation-originale': 'creation-originale',
      livre: 'livre',
      book: 'livre',
      dictionnaire: 'dictionnaire',
      dictionary: 'dictionnaire',
      lecon: 'cours-breton',
      'lecon-de-breton': 'cours-breton',
      'cours-breton': 'cours-breton',
      'cours-de-breton': 'cours-breton',
      'manuel-scolaire': 'cours-breton',
      journal: 'presse-media',
      presse: 'presse-media',
      'presse-article': 'presse-media',
      media: 'presse-media',
      archive: 'archives',
      archives: 'archives',
      'archive-dastum': 'archives',
      dastum: 'archives',
      conversation: 'conversation',
      'locuteur-natif': 'conversation',
      reference: 'reference',
      'corpus-reference': 'corpus-reference',
    };
    return aliases[normalized] || normalized;
  }

  private canonicalClassValue(value?: string | null): string {
    const normalized = (value ?? '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/&/g, 'et')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const aliases: Record<string, string> = {
      tiarvretonned: 'ti-ar-vretonned',
      'ti-ar-vretoned': 'ti-ar-vretonned',
      'ti-ar-vretonned': 'ti-ar-vretonned',
      'ti-ar-vretonned-classe': 'ti-ar-vretonned',
      'skol-an-emsav': 'skol-an-emsav',
      'skol-an-emsav-classe': 'skol-an-emsav',
    };
    return aliases[normalized] || normalized;
  }

  private canonicalSchoolLevel(value?: string | null): string {
    const normalized = (value ?? '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const aliases: Record<string, string> = {
      '1': 'niveau-1',
      'niveau-1': 'niveau-1',
      'level-1': 'niveau-1',
      '2': 'niveau-2',
      'niveau-2': 'niveau-2',
      'level-2': 'niveau-2',
      '3': 'niveau-3',
      'niveau-3': 'niveau-3',
      'level-3': 'niveau-3',
      '4': 'niveau-4',
      'niveau-4': 'niveau-4',
      'level-4': 'niveau-4',
    };
    return aliases[normalized] || normalized;
  }

  private schoolLevelFromEmail(email?: string | null): string {
    const match = (email ?? '').toLowerCase().match(/^(?:tiar|emsav)([1-4])@/);
    return match ? `niveau-${match[1]}` : '';
  }
}
