import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import {
  AdminDataOverview,
  AdminDataService,
  AdminDataset,
  AdminQualityReport,
  AdminSegment,
  AdminStorageInfo,
} from '../../core/admin-data.service';
import { AdminUserUpdate, AuthService, AuthUser } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';
import { ApiService, Phrase } from '../../core/api.service';

type AdminSection = 'recordings' | 'phrases' | 'accounts' | 'data';

@Component({
  selector: 'app-v2-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-admin.component.html',
  styleUrls: ['./v2-admin.component.scss'],
})
export class V2AdminComponent implements OnInit {
  @ViewChild('adminPlayer') private adminPlayer?: ElementRef<HTMLAudioElement>;
  overview: AdminDataOverview | null = null;
  storage: AdminStorageInfo | null = null;
  quality: AdminQualityReport | null = null;
  datasets: AdminDataset[] = [];
  segments: AdminSegment[] = [];
  users: AuthUser[] = [];
  phrases: Phrase[] = [];
  selectedSegment: AdminSegment | null = null;
  selectedSegmentSourceChoice = '';
  selectedSegmentDomainChoice = '';
  selectedSegmentRegionChoice = '';
  deletionCandidate: AdminSegment | null = null;
  selectedUser: AuthUser | null = null;
  selectedPhrase: Phrase | null = null;
  selectedPhraseSourceChoice = '';
  phraseDeletionCandidate: Phrase | null = null;
  private selectedUserOriginal: AuthUser | null = null;
  activeSection: AdminSection = 'recordings';
  readonly roles: AuthUser['role'][] = ['admin', 'teacher', 'contributor', 'learner'];
  readonly bretonLevels = ['undefined', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'native'];
  readonly phraseLevels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
  readonly phraseThemes = ['vie-quotidienne', 'education', 'famille', 'travail', 'nature', 'transports', 'sante', 'culture-patrimoine', 'histoire', 'traditions-fetes', 'cuisine', 'sports-loisirs', 'technologies', 'administration', 'non-classe'];
  readonly speakerRegions = ['Kerne (Cornouaille)', 'Leon (Léon)', 'Treger (Trégor)', 'Gwened (Vannetais)', 'Autre'];
  readonly phraseSources = [
    { value: 'livre', label: 'Livre' }, { value: 'manuel-scolaire', label: 'Manuel scolaire' },
    { value: 'cours-breton', label: 'Cours de breton' }, { value: 'presse-article', label: 'Presse / Article' },
    { value: 'internet', label: 'Internet' },
    { value: 'conversation', label: 'Conversation' }, { value: 'locuteur-natif', label: 'Locuteur natif' },
    { value: 'enregistrement-personnel', label: 'Enregistrement personnel' }, { value: 'archive', label: 'Archive' },
    { value: 'creation-originale', label: 'Création originale' }, { value: 'autre', label: 'Autre' },
  ];

  query = '';
  phraseQuery = '';
  phraseSort: 'recent' | 'phrase' | 'author' | 'theme' | 'level' | 'source' = 'recent';
  phraseSortDirection: 'asc' | 'desc' = 'asc';
  recordingSort: 'phrase' | 'dataset' | 'status' = 'phrase';
  recordingSortDirection: 'asc' | 'desc' = 'asc';
  datasetFilter = '';
  statusFilter = '';
  loading = true;
  saving = false;
  deletingSegmentId: number | null = null;
  userSaving = false;
  error: string | null = null;
  success: string | null = null;
  private userLoadInFlight = false;
  activeSegmentAudioId: number | null = null;
  isPlayingSegmentAudio = false;
  readonly waveformBars = [12, 20, 30, 16, 22, 14, 28, 36, 18, 12, 24, 16, 10, 20, 14, 8];

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly route: ActivatedRoute,
    private readonly adminData: AdminDataService,
    private readonly api: ApiService,
  ) {}

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((params) => {
      this.activeSection = this.sectionFromParam(params.get('section'));
    });
    this.load();
  }

  get isAdmin(): boolean {
    return this.auth.user()?.role === 'admin';
  }

  get adminUsersCount(): number {
    return this.users.filter((user) => user.role === 'admin').length;
  }

  get teacherUsersCount(): number {
    return this.users.filter((user) => user.role === 'teacher').length;
  }

  get activeUsersCount(): number {
    return this.users.filter((user) => user.active).length;
  }

  get selectedUserDirty(): boolean {
    return !!this.selectedUser && JSON.stringify(this.selectedUser) !== JSON.stringify(this.selectedUserOriginal);
  }

  get filteredPhrases(): Phrase[] {
    const query = this.phraseQuery.trim().toLocaleLowerCase();
    const filtered = this.phrases.filter((phrase) => {
      const matchesQuery = !query || [phrase.texte, phrase.traduction_fr, phrase.auteur, phrase.source]
        .some((value) => value?.toLocaleLowerCase().includes(query));
      return matchesQuery;
    });
    return filtered.sort((a, b) => {
      let comparison = 0;
      if (this.phraseSort === 'phrase') {
        comparison = a.texte.localeCompare(b.texte, 'fr');
      } else if (this.phraseSort === 'author') {
        comparison = (a.auteur || 'zzzz').localeCompare(b.auteur || 'zzzz', 'fr')
          || a.texte.localeCompare(b.texte, 'fr');
      } else if (this.phraseSort === 'theme') {
        comparison = (a.theme || 'zzzz').localeCompare(b.theme || 'zzzz', 'fr')
          || (a.niveau || 'zz').localeCompare(b.niveau || 'zz', 'fr')
          || a.texte.localeCompare(b.texte, 'fr');
      } else if (this.phraseSort === 'level') {
        comparison = (a.niveau || 'zz').localeCompare(b.niveau || 'zz', 'fr')
          || (a.theme || 'zzzz').localeCompare(b.theme || 'zzzz', 'fr')
          || a.texte.localeCompare(b.texte, 'fr');
      } else if (this.phraseSort === 'source') {
        comparison = (a.source || 'zzzz').localeCompare(b.source || 'zzzz', 'fr')
          || a.texte.localeCompare(b.texte, 'fr');
      } else {
        return b.id - a.id;
      }
      return this.phraseSortDirection === 'asc' ? comparison : -comparison;
    });
  }

  get displayedSegments(): AdminSegment[] {
    return [...this.segments].sort((a, b) => {
      const left = this.recordingSort === 'phrase' ? a.texte : this.recordingSort === 'dataset' ? a.dataset : a.status;
      const right = this.recordingSort === 'phrase' ? b.texte : this.recordingSort === 'dataset' ? b.dataset : b.status;
      const comparison = (left || '').localeCompare(right || '', 'fr');
      return this.recordingSortDirection === 'asc' ? comparison : -comparison;
    });
  }

  sortRecordingsBy(column: 'phrase' | 'dataset' | 'status'): void {
    if (this.recordingSort === column) {
      this.recordingSortDirection = this.recordingSortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.recordingSort = column;
    this.recordingSortDirection = 'asc';
  }

  recordingSortIndicator(column: 'phrase' | 'dataset' | 'status'): string {
    return this.recordingSort === column ? (this.recordingSortDirection === 'asc' ? '▲' : '▼') : '△';
  }

  sortPhrasesBy(column: 'phrase' | 'author' | 'theme' | 'level' | 'source'): void {
    if (this.phraseSort === column) {
      this.phraseSortDirection = this.phraseSortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.phraseSort = column;
    this.phraseSortDirection = 'asc';
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
    }
  }

  load(): void {
    if (this.auth.token() && !this.auth.user()) {
      if (this.userLoadInFlight) return;
      this.userLoadInFlight = true;
      this.loading = true;
      this.auth.me().subscribe({
        next: () => {
          this.userLoadInFlight = false;
          this.load();
        },
        error: (err) => {
          this.userLoadInFlight = false;
          this.error = this.errorDetail(err, 'Session administrateur impossible a verifier.');
          this.loading = false;
        },
      });
      return;
    }

    if (!this.isAdmin) {
      this.loading = false;
      return;
    }
    this.loading = true;
    this.error = null;
    this.success = null;

    this.adminData.overview().subscribe({
      next: (overview) => {
        this.overview = overview;
        this.loadSupportingData();
        this.loadSegments();
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Chargement administration impossible.');
        this.loading = false;
      },
    });
  }

  isSection(section: AdminSection): boolean {
    return this.activeSection === section;
  }

  loadSegments(): void {
    if (!this.isAdmin) return;
    this.loading = true;
    this.error = null;
    this.adminData.segments({
      query: this.query,
      dataset: this.datasetFilter,
      status: this.statusFilter,
    }).subscribe({
      next: (segments) => {
        this.segments = segments;
        if (this.selectedSegment && !segments.some((item) => item.id === this.selectedSegment?.id)) {
          this.selectedSegment = null;
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Chargement des enregistrements impossible.');
        this.loading = false;
      },
    });
  }

  edit(segment: AdminSegment): void {
    this.selectedSegment = { ...segment };
    this.selectedSegmentSourceChoice = this.metadataChoice(this.phraseSources.map((item) => item.value), segment.source);
    this.selectedSegmentDomainChoice = this.metadataChoice(this.phraseThemes, segment.domain);
    this.selectedSegmentRegionChoice = this.metadataChoice(this.speakerRegions, segment.speaker_region);
    this.selectedUser = null;
    this.success = null;
    this.error = null;
  }

  changeSegmentSource(value: string): void {
    this.selectedSegmentSourceChoice = value;
    if (!this.selectedSegment) return;
    if (value !== 'autre') this.selectedSegment.source = value || null;
    else if (this.phraseSources.some((source) => source.value === this.selectedSegment?.source)) this.selectedSegment.source = '';
    if (value !== 'internet') this.selectedSegment.source_url = null;
  }

  changeSegmentDomain(value: string): void {
    this.selectedSegmentDomainChoice = value;
    if (!this.selectedSegment) return;
    if (value !== 'autre') this.selectedSegment.domain = value || null;
    else if (this.phraseThemes.includes(this.selectedSegment.domain || '')) this.selectedSegment.domain = '';
  }

  changeSegmentRegion(value: string): void {
    this.selectedSegmentRegionChoice = value;
    if (!this.selectedSegment) return;
    if (value !== 'Autre') this.selectedSegment.speaker_region = value || null;
    else if (this.speakerRegions.includes(this.selectedSegment.speaker_region || '')) this.selectedSegment.speaker_region = '';
  }

  toggleSegmentAudio(segment: AdminSegment): void {
    const player = this.adminPlayer?.nativeElement;
    if (!player) return;
    if (this.activeSegmentAudioId === segment.id && this.isPlayingSegmentAudio) {
      player.pause();
      return;
    }
    if (this.activeSegmentAudioId !== segment.id) {
      player.src = segment.audio_url;
      player.load();
      this.activeSegmentAudioId = segment.id;
    }
    player.play().then(() => this.isPlayingSegmentAudio = true).catch(() => {
      this.isPlayingSegmentAudio = false;
      this.error = 'Lecture audio impossible.';
    });
  }

  isSegmentPlaying(segment: AdminSegment): boolean {
    return this.activeSegmentAudioId === segment.id && this.isPlayingSegmentAudio;
  }

  onSegmentPlaybackStopped(): void {
    this.isPlayingSegmentAudio = false;
  }

  editUser(user: AuthUser): void {
    this.selectedUser = { ...user };
    this.selectedUserOriginal = { ...user };
    this.selectedSegment = null;
    this.success = null;
    this.error = null;
  }

  editPhrase(phrase: Phrase): void {
    this.selectedPhrase = { ...phrase };
    this.selectedPhraseSourceChoice = this.phraseSources.some((source) => source.value === phrase.source)
      ? phrase.source || ''
      : phrase.source ? 'autre' : '';
    this.error = null;
    this.success = null;
  }

  changeSelectedPhraseSource(value: string): void {
    this.selectedPhraseSourceChoice = value;
    if (!this.selectedPhrase) return;
    if (value !== 'autre') this.selectedPhrase.source = value || null;
    else if (this.phraseSources.some((source) => source.value === this.selectedPhrase?.source)) this.selectedPhrase.source = '';
  }

  saveSelectedPhrase(): void {
    const phrase = this.selectedPhrase;
    if (!phrase || this.saving || !phrase.texte.trim() || !phrase.theme || !phrase.niveau) return;
    this.saving = true;
    this.error = null;
    this.api.updatePhrase(phrase.id, {
      texte: phrase.texte.trim(),
      traduction_fr: phrase.traduction_fr?.trim() || null,
      theme: phrase.theme,
      niveau: phrase.niveau,
      source: phrase.source?.trim() || null,
      auteur: phrase.auteur?.trim() || null,
      langue: phrase.langue || 'br',
    }).subscribe({
      next: (updated) => {
        this.phrases = this.phrases.map((item) => item.id === updated.id ? updated : item);
        this.selectedPhrase = null;
        this.saving = false;
        this.success = 'Phrase mise à jour.';
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Modification de la phrase impossible.');
        this.saving = false;
      },
    });
  }

  confirmPhraseDelete(): void {
    const phrase = this.phraseDeletionCandidate;
    if (!phrase || this.saving) return;
    this.saving = true;
    this.error = null;
    this.api.deletePhrase(phrase.id).subscribe({
      next: () => {
        this.phrases = this.phrases.filter((item) => item.id !== phrase.id);
        this.phraseDeletionCandidate = null;
        this.selectedPhrase = null;
        this.saving = false;
        this.success = 'Phrase supprimée.';
        this.refreshOverview();
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Suppression de la phrase impossible.');
        this.phraseDeletionCandidate = null;
        this.saving = false;
      },
    });
  }

  closeUserEditor(): void {
    if (this.userSaving) return;
    this.selectedUser = null;
    this.selectedUserOriginal = null;
  }

  saveSelectedUser(): void {
    if (!this.selectedUser || this.userSaving) return;
    this.userSaving = true;
    this.error = null;
    this.success = null;
    const user = this.selectedUser;
    const payload: AdminUserUpdate = {
      display_name: user.display_name,
      role: user.role,
      breton_level: user.breton_level,
      organization: user.organization || null,
      school: user.school || null,
      school_level: user.school_level || null,
      comments: user.comments || null,
      must_change_password: user.must_change_password,
      active: user.active,
    };

    this.auth.updateUser(user.id, payload).subscribe({
      next: (updated) => {
        this.users = this.users.map((item) => item.id === updated.id ? updated : item);
        this.selectedUser = { ...updated };
        this.selectedUserOriginal = { ...updated };
        this.success = 'Compte mis a jour.';
        this.userSaving = false;
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Mise a jour du compte impossible.');
        this.userSaving = false;
      },
    });
  }

  toggleSelectedUserActive(active: boolean): void {
    if (!this.selectedUser || this.userSaving || this.isCurrentUser(this.selectedUser)) return;
    this.selectedUser = { ...this.selectedUser, active };
    this.saveSelectedUser();
  }

  isCurrentUser(user: AuthUser | null): boolean {
    return !!user && this.auth.user()?.id === user.id;
  }

  saveSelected(): void {
    if (!this.selectedSegment || this.saving) return;
    this.saving = true;
    this.error = null;
    this.success = null;
    const segment = this.selectedSegment;

    this.adminData.updateSegment(segment.id, {
      texte: segment.texte,
      traduction_fr: segment.traduction_fr,
      source: segment.source,
      source_url: segment.source_url,
      domain: segment.domain,
      level: segment.level,
      speaker_region: segment.speaker_region,
      speaker_city: segment.speaker_city,
      speaker_accent: segment.speaker_accent,
      speaker_level: segment.speaker_level,
      contributor_name: segment.contributor_name,
      status: segment.status,
    }).subscribe({
      next: (updated) => {
        this.segments = this.segments.map((item) => item.id === updated.id ? updated : item);
        this.selectedSegment = { ...updated };
        this.success = 'Enregistrement mis a jour.';
        this.saving = false;
        this.refreshOverview();
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Mise a jour impossible.');
        this.saving = false;
      },
    });
  }

  private metadataChoice(values: string[], current?: string | null): string {
    if (!current) return '';
    return values.includes(current) ? current : values.includes('Autre') ? 'Autre' : 'autre';
  }

  deleteSelected(): void {
    if (!this.selectedSegment) return;
    this.requestDelete(this.selectedSegment);
  }

  requestDelete(segment: AdminSegment): void {
    if (this.saving || this.deletingSegmentId !== null) return;
    this.deletionCandidate = segment;
  }

  cancelDelete(): void {
    if (this.deletingSegmentId !== null) return;
    this.deletionCandidate = null;
  }

  confirmDelete(): void {
    const segment = this.deletionCandidate;
    if (!segment || this.saving || this.deletingSegmentId !== null) return;

    const id = segment.id;
    this.deletingSegmentId = id;
    this.error = null;
    this.success = null;

    this.adminData.deleteSegmentAudio(id).subscribe({
      next: () => {
        this.segments = this.segments.filter((item) => item.id !== id);
        if (this.selectedSegment?.id === id) this.selectedSegment = null;
        this.deletionCandidate = null;
        this.success = 'Audio supprime.';
        this.deletingSegmentId = null;
        this.refreshOverview();
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Suppression impossible.');
        this.deletingSegmentId = null;
      },
    });
  }

  runStorageCheck(): void {
    if (!this.isAdmin) return;
    this.loading = true;
    this.adminData.quality(true).subscribe({
      next: (quality) => {
        this.quality = quality;
        this.loading = false;
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Verification stockage impossible.');
        this.loading = false;
      },
    });
  }

  statusLabel(status: string): string {
    if (status === 'approved') return 'Valide';
    if (status === 'rejected') return 'A revoir';
    return 'A evaluer';
  }

  statusClass(status: string): string {
    if (status === 'approved') return 'ok';
    if (status === 'rejected') return 'review';
    return 'todo';
  }

  exportDataset(dataset: AdminDataset): void {
    this.error = null;
    this.success = null;
    this.adminData.exportDataset(dataset.name, { format: 'csv' }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${dataset.name}-dataset.zip`;
        link.click();
        URL.revokeObjectURL(url);
        this.success = `Export prepare pour ${dataset.name}.`;
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Export dataset impossible.');
      },
    });
  }

  previewCleanDataset(dataset: AdminDataset): void {
    this.error = null;
    this.success = null;
    this.adminData.cleanDataset(dataset.name, {
      dry_run: true,
      remove_missing_storage_audios: true,
    }).subscribe({
      next: (result) => {
        this.success = `${dataset.name}: ${result.phrase_ids_without_audio.length} phrase(s) sans audio, ${result.missing_storage_audio_ids.length} audio(s) manquant(s).`;
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Analyse dataset impossible.');
      },
    });
  }

  clearImportedDataset(dataset: AdminDataset): void {
    if (!confirm(`Vider les audios importes du dataset "${dataset.name}" ? Les enregistrements utilisateurs seront conserves.`)) return;
    this.error = null;
    this.success = null;
    this.adminData.clearDataset(dataset.name, {
      dry_run: false,
      include_user_data: false,
    }).subscribe({
      next: (result) => {
        this.success = `${dataset.name}: ${result.deleted_audios} audio(s) importes supprime(s), ${result.protected_user_audio_ids.length} audio(s) utilisateur conserve(s).`;
        this.load();
      },
      error: (err) => {
        this.error = this.errorDetail(err, 'Vidage dataset impossible.');
      },
    });
  }

  private loadSupportingData(): void {
    this.adminData.datasets().subscribe({ next: (datasets) => this.datasets = datasets, error: () => {} });
    this.adminData.storage().subscribe({ next: (storage) => this.storage = storage, error: () => {} });
    this.adminData.quality(false).subscribe({ next: (quality) => this.quality = quality, error: () => {} });
    this.auth.listUsers().subscribe({ next: (users) => this.users = users, error: () => {} });
    this.api.getPhrases().subscribe({ next: (phrases) => this.phrases = phrases, error: () => {} });
  }

  private refreshOverview(): void {
    this.adminData.overview().subscribe({ next: (overview) => this.overview = overview, error: () => {} });
  }

  private errorDetail(err: any, fallback: string): string {
    return err?.error?.detail || err?.message || fallback;
  }

  private sectionFromParam(value: string | null): AdminSection {
    if (value === 'phrases') return 'phrases';
    if (value === 'accounts') return 'accounts';
    if (value === 'data') return 'data';
    return 'recordings';
  }
}
