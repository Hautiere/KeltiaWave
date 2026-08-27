import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, finalize, map } from 'rxjs/operators';
import { ValidationsService } from '../../core/validations.service';
import { ApiService, Phrase } from '../../core/api.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { I18nService, type AppLanguage } from '../../core/i18n.service';

const BRETON_AVATARS = [
  '/assets/fanch-avatar-bzh-01.webp',
  '/assets/fanch-avatar-bzh-02.webp',
  '/assets/fanch-avatar-bzh-03.webp',
  '/assets/fanch-avatar-bzh-04.webp',
  '/assets/fanch-avatar-bzh-05.webp',
  '/assets/fanch-avatar-bzh-06.webp',
];

const CYMRU_AVATARS = [
  '/assets/fanch-avatar-cymru-flag.webp',
  '/assets/fanch-avatar-cymru-coffee.webp',
  '/assets/fanch-avatar-cymru-kilt.webp',
  '/assets/fanch-avatar-cymru-rugby.webp',
];

@Component({
  selector: 'app-accueil',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe],
  templateUrl: './accueil.component.html',
  styleUrls: ['./accueil.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccueilComponent implements OnInit {
  loading = false;
  error: string | null = null;
  pending = 0;
  approved = 0;
  rejected = 0;
  phrases: Phrase[] = [];
  readonly avatarSrc = computed(() => this.randomAvatarFor(this.i18n.language()));

  constructor(
    private readonly validations: ValidationsService,
    private readonly api: ApiService,
    private readonly i18n: I18nService,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  get featuredPhrase(): Phrase | null {
    return this.phrases[0] ?? null;
  }

  ngOnInit(): void {
    this.loading = true;
    forkJoin({
      phrases: this.api.getPhrases().pipe(catchError(() => {
        this.error = 'Unable to load phrases right now.';
        return of([]);
      })),
      pending: this.validations.listByStatus('pending').pipe(catchError(() => of([]))),
      approved: this.validations.listByStatus('approved').pipe(catchError(() => of([]))),
      rejected: this.validations.listByStatus('rejected').pipe(catchError(() => of([]))),
    })
    .pipe(
      map(({ phrases, pending, approved, rejected }) => ({
        phrases,
        pending: pending.length,
        approved: approved.length,
        rejected: rejected.length,
      })),
      finalize(() => {
        this.loading = false;
        this.cdr.markForCheck();
      })
    )
    .subscribe({
      next: ({ phrases, pending, approved, rejected }) => {
        this.phrases = phrases;
        this.pending = pending;
        this.approved = approved;
        this.rejected = rejected;
      },
      error: (err) => {
        this.error = err?.message ?? 'Loading error';
        this.cdr.markForCheck();
      },
    });
  }

  private randomAvatarFor(language: AppLanguage): string {
    const avatars = language === 'en' || language === 'cy' ? CYMRU_AVATARS : BRETON_AVATARS;
    return avatars[Math.floor(Math.random() * avatars.length)];
  }
}
