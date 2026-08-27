import { CommonModule } from '@angular/common';
import { Component, OnInit, effect, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  AdminDataOverview,
  AdminDataService,
  AdminDataset,
  AdminQualityReport,
  AdminSegment,
  AdminStorageInfo,
} from '../../core/admin-data.service';
import { AuthService, AuthUser } from '../../core/auth.service';
import { I18nService } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import {
  LEVEL_OPTIONS,
  ROLE_OPTIONS,
  UserProfile,
  UserRole,
} from '../../core/profile.service';

type RoleFilter = 'all' | UserRole;
type AdminSection = 'users' | 'data';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss'],
})
export class AdminComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly adminData = inject(AdminDataService);
  private readonly i18n = inject(I18nService);
  private readonly route = inject(ActivatedRoute);
  private loadedForAdminId: number | null = null;

  readonly roles = ROLE_OPTIONS;
  readonly levels = LEVEL_OPTIONS;

  users: AuthUser[] = [];
  selected: AuthUser | null = null;
  query = '';
  roleFilter: RoleFilter = 'all';
  loading = false;
  savingId: number | null = null;
  message: string | null = null;
  error: string | null = null;
  section: AdminSection = 'users';
  dataLoading = false;
  dataError: string | null = null;
  overview: AdminDataOverview | null = null;
  storage: AdminStorageInfo | null = null;
  datasets: AdminDataset[] = [];
  segments: AdminSegment[] = [];
  quality: AdminQualityReport | null = null;
  selectedSegment: AdminSegment | null = null;
  segmentQuery = '';
  datasetFilter = '';
  segmentStatusFilter = '';
  savingSegmentId: number | null = null;

  constructor() {
    effect(() => {
      const user = this.auth.user();
      if (user?.role !== 'admin' || this.loadedForAdminId === user.id) return;
      this.loadedForAdminId = user.id;
      this.load();
    });
  }

  get currentUser(): AuthUser | null {
    return this.auth.user();
  }

  get isAdmin(): boolean {
    return this.currentUser?.role === 'admin';
  }

  get filteredUsers(): AuthUser[] {
    const q = this.query.trim().toLowerCase();
    return this.users.filter((user) => {
      const matchesQuery = !q
        || user.display_name.toLowerCase().includes(q)
        || user.email.toLowerCase().includes(q)
        || (user.organization ?? '').toLowerCase().includes(q)
        || (user.comments ?? '').toLowerCase().includes(q);
      const matchesRole = this.roleFilter === 'all' || user.role === this.roleFilter;
      return matchesQuery && matchesRole;
    });
  }

  get learnerCount(): number {
    return this.users.filter((user) => user.role === 'learner').length;
  }

  get teacherCount(): number {
    return this.users.filter((user) => user.role === 'teacher').length;
  }

  get adminCount(): number {
    return this.users.filter((user) => user.role === 'admin').length;
  }

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((params) => {
      const section = params.get('section') === 'data' ? 'data' : 'users';
      this.showSection(section);
    });
  }

  load(): void {
    this.loading = true;
    this.message = null;
    this.error = null;
    this.auth.listUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.syncSelected();
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || this.i18n.translate('admin.loadError');
        this.loading = false;
      },
    });
  }

  showSection(section: AdminSection): void {
    this.section = section;
    this.message = null;
    this.error = null;
    if (section === 'data' && !this.overview) this.loadData();
  }

  refreshCurrentSection(): void {
    if (this.section === 'data') {
      this.loadData();
      return;
    }
    this.load();
  }

  loadData(): void {
    this.dataLoading = true;
    this.dataError = null;
    forkJoin({
      overview: this.adminData.overview(),
      storage: this.adminData.storage(),
      datasets: this.adminData.datasets(),
      segments: this.adminData.segments({
        query: this.segmentQuery,
        dataset: this.datasetFilter,
        status: this.segmentStatusFilter,
      }),
      quality: this.adminData.quality(),
    }).subscribe({
      next: ({ overview, storage, datasets, segments, quality }) => {
        this.overview = overview;
        this.storage = storage;
        this.datasets = datasets;
        this.segments = segments;
        this.quality = quality;
        this.syncSelectedSegment();
        this.dataLoading = false;
      },
      error: (err) => {
        this.dataError = this.errorDetail(err, 'Impossible de charger les donnees du corpus.');
        this.dataLoading = false;
      },
    });
  }

  loadSegments(): void {
    this.dataLoading = true;
    this.dataError = null;
    this.adminData.segments({
      query: this.segmentQuery,
      dataset: this.datasetFilter,
      status: this.segmentStatusFilter,
    }).subscribe({
      next: (segments) => {
        this.segments = segments;
        this.syncSelectedSegment();
        this.dataLoading = false;
      },
      error: (err) => {
        this.dataError = this.errorDetail(err, 'Impossible de charger les segments.');
        this.dataLoading = false;
      },
    });
  }

  runStorageCheck(): void {
    this.dataLoading = true;
    this.adminData.quality(true).subscribe({
      next: (quality) => {
        this.quality = quality;
        this.dataLoading = false;
      },
      error: (err) => {
        this.dataError = this.errorDetail(err, 'Impossible de verifier le stockage audio.');
        this.dataLoading = false;
      },
    });
  }

  editSegment(segment: AdminSegment): void {
    this.selectedSegment = { ...segment };
    this.message = null;
    this.dataError = null;
  }

  saveSegment(): void {
    if (!this.selectedSegment) return;
    const segment = this.selectedSegment;
    this.savingSegmentId = segment.id;
    this.adminData.updateSegment(segment.id, {
      texte: segment.texte,
      source: segment.source,
      domain: segment.domain,
      status: segment.status,
    }).subscribe({
      next: (updated) => {
        this.segments = this.segments.map((item) => item.id === updated.id ? updated : item);
        this.selectedSegment = { ...updated };
        this.message = this.i18n.translate('adminData.saved');
        this.savingSegmentId = null;
        this.refreshDataSummaries();
      },
      error: (err) => {
        this.dataError = this.errorDetail(err, 'Impossible de mettre a jour le segment.');
        this.savingSegmentId = null;
      },
    });
  }

  deleteSegmentAudio(segment: AdminSegment): void {
    if (!confirm(this.i18n.translate('adminData.confirmDelete'))) return;
    this.savingSegmentId = segment.id;
    this.adminData.deleteSegmentAudio(segment.id).subscribe({
      next: () => {
        this.segments = this.segments.filter((item) => item.id !== segment.id);
        if (this.selectedSegment?.id === segment.id) this.selectedSegment = null;
        this.message = this.i18n.translate('adminData.deleted');
        this.savingSegmentId = null;
        this.refreshDataSummaries();
      },
      error: (err) => {
        this.dataError = this.errorDetail(err, 'Impossible de supprimer cet audio.');
        this.savingSegmentId = null;
      },
    });
  }

  edit(user: AuthUser): void {
    this.selected = { ...user };
    this.message = null;
    this.error = null;
  }

  cancelEdit(): void {
    this.selected = null;
  }

  saveSelected(): void {
    if (!this.selected) return;
    const user = this.selected;
    this.savingId = user.id;
    this.message = null;
    this.error = null;
    this.auth.updateUser(user.id, {
      display_name: user.display_name,
      role: user.role,
      breton_level: user.breton_level,
      organization: user.organization || null,
      comments: user.comments || null,
      active: user.active,
    }).subscribe({
      next: (updated) => {
        this.users = this.users.map((item) => item.id === updated.id ? updated : item);
        this.selected = { ...updated };
        this.message = this.i18n.translate('admin.saved');
        this.savingId = null;
      },
      error: (err) => {
        this.error = err?.error?.detail || this.i18n.translate('admin.saveError');
        this.savingId = null;
      },
    });
  }

  delete(user: AuthUser): void {
    if (user.id === this.currentUser?.id) return;
    if (!confirm(this.i18n.translate('admin.confirmDelete'))) return;

    this.savingId = user.id;
    this.message = null;
    this.error = null;
    this.auth.deleteUser(user.id).subscribe({
      next: () => {
        this.users = this.users.filter((item) => item.id !== user.id);
        if (this.selected?.id === user.id) this.selected = null;
        this.message = this.i18n.translate('admin.deleted');
        this.savingId = null;
      },
      error: (err) => {
        this.error = err?.error?.detail || this.i18n.translate('admin.deleteError');
        this.savingId = null;
      },
    });
  }

  roleLabelFor(role: UserProfile['role']): string {
    return this.i18n.translate(`profile.role.${role}`);
  }

  levelLabelFor(value: string | null | undefined): string {
    const level = this.levels.find((item) => item.value === (value ?? 'undefined'));
    return level ? this.i18n.translate(level.labelKey) : value ?? '';
  }

  private syncSelected(): void {
    if (!this.selected) return;
    const updated = this.users.find((user) => user.id === this.selected?.id);
    this.selected = updated ? { ...updated } : null;
  }

  private syncSelectedSegment(): void {
    if (!this.selectedSegment) return;
    const updated = this.segments.find((segment) => segment.id === this.selectedSegment?.id);
    this.selectedSegment = updated ? { ...updated } : null;
  }

  private refreshDataSummaries(): void {
    forkJoin({
      overview: this.adminData.overview(),
      datasets: this.adminData.datasets(),
      quality: this.adminData.quality(),
    }).subscribe({
      next: ({ overview, datasets, quality }) => {
        this.overview = overview;
        this.datasets = datasets;
        this.quality = quality;
      },
    });
  }

  private errorDetail(err: any, fallback: string): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || JSON.stringify(item)).join(' ');
    }
    return fallback;
  }
}
