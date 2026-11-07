import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, AfterViewInit, OnChanges, OnDestroy, Output, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import type { Phrase, AudioRead } from '../../../core/api.service';
import { DOMAIN_OPTIONS, canonicalDomain } from '../../../core/domains';
import { subdomainsFor } from '../../../core/subdomains';
import type { AppLanguage } from '../../../core/i18n.service';
import { I18nService } from '../../../core/i18n.service';
import { audioFileUrl } from '../../../core/constants';
import { audioAttribution } from '../../../core/audio-attribution';
import { mobileToolLinks, mobileLabel } from '../../../../../../shared/mobile-tools';
import { EXPLORER_COPY } from './komz-explorer.copy';
import { ExplorerState, initialExplorerState, filterExplorerPhrases, mobileSubdomainLabel } from './komz-explorer.model';
import { KomzIconComponent } from './komz-icon.component';

@Component({ selector: 'app-komz-explorer', standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, KomzIconComponent],
  templateUrl: './komz-explorer.component.html', styleUrls: ['./komz-explorer.component.scss'] })
export class KomzExplorerComponent implements OnChanges, OnDestroy, AfterViewInit {
  @ViewChild('toolTabs') toolTabs?: ElementRef<HTMLElement>;
  tabsCanGoBack = false;
  tabsCanGoForward = false;
  private tabsResizeObserver?: ResizeObserver;
  ngAfterViewInit(): void {
    const tabs = this.toolTabs?.nativeElement;
    if (!tabs) return;
    this.tabsResizeObserver = new ResizeObserver(() => this.updateTabsOverflow());
    this.tabsResizeObserver.observe(tabs);
  }
  updateTabsOverflow(): void {
    const tabs = this.toolTabs?.nativeElement;
    if (!tabs) return;
    this.tabsCanGoBack = tabs.scrollLeft > 1;
    this.tabsCanGoForward = tabs.scrollLeft + tabs.clientWidth < tabs.scrollWidth - 1;
  }
  scrollTabs(direction: number): void {
    const tabs = this.toolTabs?.nativeElement;
    tabs?.scrollBy({ left: direction * tabs.clientWidth * 0.7, behavior: 'smooth' });
  }
  @Input() experience: 'komz' | 'listen' = 'komz';
  @ViewChild('referencePlayer') player?: ElementRef<HTMLAudioElement>;
  playingId: number | null = null;
  audioError = false;
  private playIntent = 0;
  private listenedReferenceIds = new Set<number>();
  @Input() phrases: Phrase[] = [];
  @Input() references: AudioRead[] = [];
  @Input() language: AppLanguage = 'fr';
  @Input() state = initialExplorerState();
  @Input() loading = false;
  @Input() error: string | null = null;
  @Input() signedIn = false;
  @Input() progress = 0;
  @Input() progressLabel = '';
  @Output() stateChange = new EventEmitter<ExplorerState>();
  @Output() practice = new EventEmitter<Phrase>();
  @Output() classic = new EventEmitter<void>();
  @Output() languageChange = new EventEmitter<AppLanguage>();
  @Output() retry = new EventEmitter<void>();
  view = initialExplorerState();
  readonly links = mobileToolLinks();
  readonly pageSize = 20;
  readonly mobileSubdomainLabel = mobileSubdomainLabel;
  themesOpen = false;
  allThemes = false;
  filtersOpen = false;
  progressOpen = false;
  private referencesByPhrase = new Map<number, AudioRead>();
  domains: Array<{ value: string; label: string; icon: string; image: string; count: number }> = [];
  facets: Array<{ value: string; label: string; icon: string; count: number }> = [];
  levels: Array<{ value: string; label: string; count: number }> = [];
  results: Phrase[] = [];
  visiblePhrases: Phrase[] = [];
  pages = 1;
  readonly themeImages: Record<string, string> = {
    rencontres: '01_meeting-people', 'maison-quotidien': '02_home-daily-life', 'famille-relations': '03_family-relationships',
    'alimentation-achats': '04_food-cooking-shopping', deplacements: '05_travel-transport', 'nature-meteo': '06_nature-environment',
    'travail-etudes': '07_work-studies', 'sante-bien-etre': '08_health-well-being', 'culture-fetes': '09_everyday-situations',
    'loisirs-sport': '10_leisure-sport', 'histoire-patrimoine': '11_culture-society', 'demarches-services': '12_practical-information',
    'numerique-technologies': '13_digital-life-technology',
  };
  readonly themeIcons: Record<string, string> = { rencontres: 'people', 'maison-quotidien': 'home', 'famille-relations': 'people', 'alimentation-achats': 'basket', deplacements: 'train', 'nature-meteo': 'leaf', 'travail-etudes': 'book', 'sante-bien-etre': 'heart', 'culture-fetes': 'chat', 'loisirs-sport': 'bars', 'histoire-patrimoine': 'book', 'demarches-services': 'pin', 'numerique-technologies': 'computer' };
  constructor(readonly i18n: I18nService) {}
  headerLabel(key: string): string { return key === 'otherTools' ? ({ fr: 'Autres outils', en: 'Other tools', br: 'Ostilhoù all', cy: 'Offer eraill' }[this.language] ?? 'Autres outils') : mobileLabel(key, this.language); }
  get copy() { return EXPLORER_COPY[this.language]; }
  get listenedCount(): number { return this.references.filter(reference => this.listenedReferenceIds.has(reference.id)).length; }
  get listenedProgress(): number { return this.references.length ? this.listenedCount / this.references.length * 100 : 0; }
  get product() { return this.experience === 'listen' ? 'Listen' : 'Komz'; }
  get listeningCopy() {
    return {
      fr: { subtitle: 'Écouter, comprendre, puis pratiquer', intro: 'Choisissez un sous-domaine et écoutez les voix de référence.', rule: 'Écoutez la référence jusqu’au bout, puis répétez et comparez.', first: 'Écoutez d’abord', practice: 'Répéter et comparer' },
      en: { subtitle: 'Listen, understand, then practise', intro: 'Choose a topic and listen to the reference voices.', rule: 'Listen to the full reference, then repeat and compare.', first: 'Listen first', practice: 'Repeat and compare' },
      br: { subtitle: 'Selaou, kompren ha pleustriñ', intro: 'Dibabit un isdomani ha selaouit ar mouezhioù dave.', rule: 'Selaouit ar vouezh dave betek ar fin, hag adlavarit ha keñveriit.', first: 'Selaouit da gentañ', practice: 'Adlavaret ha keñveriañ' },
      cy: { subtitle: 'Gwrando, deall, yna ymarfer', intro: 'Dewiswch is-bwnc a gwrandewch ar y lleisiau cyfeirio.', rule: 'Gwrandewch ar y cyfeiriad cyfan, yna ailadroddwch a chymharwch.', first: 'Gwrandewch yn gyntaf', practice: 'Ailadrodd a chymharu' },
    }[this.language];
  }
  get selectedDomain() { return this.domains.find(domain => domain.value === this.view.theme); }
  get visibleDomains() { return this.allThemes ? this.domains : this.domains.slice(0, 5); }
  get translationLanguage(): 'fr' | 'en' | 'cy' | 'none' {
    return this.view.translation === 'interface' ? (this.language === 'br' ? 'none' : this.language) : this.view.translation;
  }
  ngOnChanges(): void {
    this.stopAudio();
    this.view = { ...this.state, onlyWithAudio: this.experience === 'listen' || this.state.onlyWithAudio };
    this.referencesByPhrase = new Map(this.references.map(audio => [audio.phrase_id, audio]));
    this.refresh();
  }
  private refresh(): void {
    const ids = new Set(this.referencesByPhrase.keys());
    this.domains = DOMAIN_OPTIONS.filter(domain => domain.value && this.phrases.some(p => canonicalDomain(p.theme) === domain.value)).map(domain => ({
      value: domain.value, label: this.i18n.translate(domain.labelKey), icon: this.themeIcons[domain.value] || 'grid',
      image: `/assets/themes/${this.themeImages[domain.value]}.jpg`,
      count: filterExplorerPhrases(this.phrases, ids, { ...this.view, theme: domain.value, level: 'all', subdomain: '', search: '' }).length,
    }));
    if (this.domains.length && !this.selectedDomain) this.view.theme = this.domains[0].value;
    const options = subdomainsFor(this.view.theme, this.language);
    const icons = ['handshake', 'user', 'pin', 'chat', 'heart', 'question'];
    const count = (patch: Partial<ExplorerState>) => filterExplorerPhrases(this.phrases, ids, { ...this.view, ...patch }).length;
    this.facets = [{ value: '', label: this.copy.all, icon: 'grid', count: count({ subdomain: '' }) },
      ...options.map((option, index) => ({ ...option, icon: this.view.theme === 'rencontres' ? icons[index] || 'grid' : this.themeIcons[this.view.theme] || 'grid', count: count({ subdomain: option.value }) })),
      { value: '__unclassified__', label: this.copy.unclassified, icon: 'book', count: count({ subdomain: '__unclassified__' }) }];
    this.levels = ['all', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'unrated'].map(value => ({ value,
      label: value === 'all' ? this.copy.allLevels : value === 'unrated' ? this.copy.unrated : value, count: count({ level: value }) }));
    this.levels = this.levels.filter(level => level.value !== 'unrated' || level.count || this.view.level === 'unrated');
    this.results = filterExplorerPhrases(this.phrases, ids, this.view);
    this.pages = Math.max(1, Math.ceil(this.results.length / this.pageSize));
    this.view.page = Math.min(this.pages, Math.max(1, this.view.page));
    this.visiblePhrases = this.results.slice((this.view.page - 1) * this.pageSize, this.view.page * this.pageSize);
  }
  change(patch: Partial<ExplorerState>): void {
    this.stopAudio();
    this.view = { ...this.view, page: 1, ...patch };
    if (this.experience === 'listen') this.view.onlyWithAudio = true;
    this.refresh(); this.stateChange.emit({ ...this.view });
  }
  chooseTheme(value: string): void {
    this.change({ theme: value, subdomain: '', level: 'all', search: '' }); this.themesOpen = false;
  }
  reset(): void { this.change({ level: 'all', subdomain: '', search: '', onlyWithAudio: true }); }
  translation(phrase: Phrase): string | null {
    return this.translationLanguage === 'none' ? null : phrase[`traduction_${this.translationLanguage}`] || null;
  }
  hasAudio(phrase: Phrase): boolean { return this.referencesByPhrase.has(phrase.id); }
  trackPhrase(_index: number, phrase: Phrase): number { return phrase.id; }
  trackValue(_index: number, value: { value: string }): string { return value.value; }
  startPractice(phrase: Phrase): void {
    if (this.experience === 'listen' && !this.canRepeat(phrase)) return;
    this.stopAudio(); this.practice.emit(phrase);
  }
  canRepeat(phrase: Phrase): boolean {
    const reference = this.referencesByPhrase.get(phrase.id);
    return !!reference && this.listenedReferenceIds.has(reference.id);
  }
  referenceName(phrase: Phrase): string {
    const reference = this.referencesByPhrase.get(phrase.id);
    return reference ? audioAttribution(reference, phrase.source) : this.copy.noReference;
  }
  ngOnDestroy(): void { this.tabsResizeObserver?.disconnect(); this.stopAudio(); }
  stopAudio(): void {
    ++this.playIntent;
    const audio = this.player?.nativeElement;
    if (audio) { audio.pause(); audio.removeAttribute('src'); audio.load(); }
    this.playingId = null;
  }
  async play(phrase: Phrase): Promise<void> {
    if (this.experience !== 'listen') return;
    if (this.playingId === phrase.id) { this.stopAudio(); return; }
    this.stopAudio(); this.audioError = false;
    const reference = this.referencesByPhrase.get(phrase.id), audio = this.player?.nativeElement;
    if (!reference || !audio) return;
    const intent = this.playIntent;
    this.playingId = phrase.id; audio.src = audioFileUrl(reference.id);
    try { await audio.play(); } catch { if (intent === this.playIntent) this.failedAudio(); }
  }
  endedAudio(): void {
    if (this.experience !== 'listen' || this.playingId === null) return;
    const reference = this.referencesByPhrase.get(this.playingId);
    if (reference) this.listenedReferenceIds.add(reference.id);
    this.playingId = null;
  }
  failedAudio(): void { if (this.playingId !== null) { this.stopAudio(); this.audioError = true; } }
}
