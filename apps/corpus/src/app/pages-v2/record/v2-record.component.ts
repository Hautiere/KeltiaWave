import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ElementRef, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom, forkJoin } from 'rxjs';
import { ApiService, AudioRead, Phrase } from '../../core/api.service';
import { WavRecorderService } from './wav-recorder.service';
import { AuthService } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';
import { DOMAIN_OPTIONS, canonicalDomain, type DomainOption } from '../../core/domains';
import { audioFileUrl } from '../../core/constants';
import { subdomainsFor, subdomainLabel } from '../../core/subdomains';

@Component({
  selector: 'app-v2-record',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-record.component.html',
  styleUrls: ['./v2-record.component.scss'],
})
export class V2RecordComponent implements OnInit, OnDestroy {
  @ViewChild('recordedPreview') private recordedPreview?: ElementRef<HTMLAudioElement>;
  phrases: Phrase[] = [];
  currentPhrase: Phrase | null = null;
  loading = true;
  submitting = false;
  error: string | null = null;
  success: string | null = null;
  submittedRecording = false;

  durationSec = 0;
  blobUrl: string | null = null;
  lastBlob: Blob | null = null;
  assessing = false;
  score: number | null = null;
  rhythmAssessment: { rhythm: number; emphasis: number; pace: number; pauses: number } | null = null;
  hfSimilarity: number | null = null;
  overallScore: number | null = null;
  recognizedText = '';
  assessmentMessage = '';
  speakerRegion = '';
  speakerLevel = '';
  stage: 'themes' | 'phrases' | 'practice' = 'themes';
  selectedTheme = '';
  selectedLevel = 'all';
  selectedSubdomain = '';
  readonly unclassifiedSubdomain = '__unclassified__';
  onlyWithAudio = true;
  approvedAudios: AudioRead[] = [];
  readonly domains = DOMAIN_OPTIONS.filter((domain) => !!domain.value);
  private readonly themeImages: Record<string, string> = {
    rencontres: '01_meeting-people.jpg',
    'maison-quotidien': '02_home-daily-life.jpg',
    'famille-relations': '03_family-relationships.jpg',
    'alimentation-achats': '04_food-cooking-shopping.jpg',
    deplacements: '05_travel-transport.jpg',
    'nature-meteo': '06_nature-environment.jpg',
    'travail-etudes': '07_work-studies.jpg',
    'sante-bien-etre': '08_health-well-being.jpg',
    'culture-fetes': '09_everyday-situations.jpg',
    'loisirs-sport': '10_leisure-sport.jpg',
    'histoire-patrimoine': '11_culture-society.jpg',
    'demarches-services': '12_practical-information.jpg',
    'numerique-technologies': '13_digital-life-technology.jpg',
  };
  private readonly referenceTranscripts = new Map<number, string>();

  private readonly completedPhraseIds = new Set<number>();

  private timer?: ReturnType<typeof setInterval>;

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
    private readonly route: ActivatedRoute,
    private readonly recorder: WavRecorderService,
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
    if (!this.currentPhrase || !this.filteredPhrases.length) return `0 / ${this.filteredPhrases.length}`;
    const index = this.filteredPhrases.findIndex((phrase) => phrase.id === this.currentPhrase?.id);
    return `${Math.max(index, 0) + 1} / ${this.filteredPhrases.length}`;
  }

  get filteredPhrases(): Phrase[] {
    return this.phrases.filter((phrase) => canonicalDomain(phrase.theme) === this.selectedTheme
      && (this.selectedLevel === 'all' || (phrase.niveau || '').toUpperCase() === this.selectedLevel)
      && this.matchesSubdomain(phrase)
      && (!this.onlyWithAudio || this.hasReference(phrase)));
  }

  get subdomainOptions() {
    return subdomainsFor(this.selectedTheme);
  }

  get subdomainCopy() {
    const labels = {
      fr: { level: 'Niveau', label: 'Sous-domaine', all: 'Tous les sous-domaines', unclassified: 'Non classées', empty: 'Aucune phrase ne correspond à ces filtres.', reset: 'Réinitialiser les filtres' },
      en: { level: 'Level', label: 'Subdomain', all: 'All subdomains', unclassified: 'Unclassified', empty: 'No phrases match these filters.', reset: 'Reset filters' },
      br: { level: 'Live', label: 'Is-tem', all: 'An holl is-temoù', unclassified: 'Disrannet ebet', empty: 'Frazenn ebet o klotañ gant ar siloù-mañ.', reset: 'Adderaouekaat ar siloù' },
      cy: { level: 'Lefel', label: 'Is thema', all: 'Pob is thema', unclassified: 'Heb eu dosbarthu', empty: 'Nid oes brawddegau sy’n cyfateb i’r hidlwyr.', reset: 'Ailosod hidlwyr' },
    };
    return labels[this.i18n.language()] || labels.fr;
  }

  levelCount(level: string): number {
    return this.themePhrases.filter((phrase) => (level === 'all' || (phrase.niveau || '').toUpperCase() === level)
      && (!this.onlyWithAudio || this.hasReference(phrase))).length;
  }

  subdomainCount(value: string): number {
    return this.themePhrases.filter((phrase) => phrase.subdomain === value
      && (!this.onlyWithAudio || this.hasReference(phrase))).length;
  }

  get unclassifiedCount(): number {
    return this.themePhrases.filter((phrase) => !phrase.subdomain
      && (!this.onlyWithAudio || this.hasReference(phrase))).length;
  }

  phraseSubdomain(phrase: Phrase): string | null {
    return subdomainLabel(this.selectedTheme, phrase.subdomain);
  }

  resetPhraseFilters(): void {
    this.selectedLevel = 'all';
    this.selectedSubdomain = '';
  }

  private matchesSubdomain(phrase: Phrase): boolean {
    if (!this.selectedSubdomain) return true;
    if (this.selectedSubdomain === this.unclassifiedSubdomain) return !phrase.subdomain;
    return phrase.subdomain === this.selectedSubdomain;
  }

  get themePhrases(): Phrase[] {
    return this.phrases.filter((phrase) => canonicalDomain(phrase.theme) === this.selectedTheme);
  }

  get availableDomains(): DomainOption[] {
    return this.domains.filter((domain) => this.phrases.some((phrase) => canonicalDomain(phrase.theme) === domain.value));
  }

  get selectedDomain(): DomainOption | undefined {
    return this.domains.find((domain) => domain.value === this.selectedTheme);
  }

  get referenceAudio(): AudioRead | undefined {
    return this.approvedAudios.find((audio) => audio.phrase_id === this.currentPhrase?.id);
  }

  hasReference(phrase: Phrase): boolean {
    return this.approvedAudios.some((audio) => audio.phrase_id === phrase.id);
  }

  get copy() {
    const labels = {
      fr: { choose: 'Choisissez un thème', intro: 'Choisissez une phrase, enregistrez votre voix, puis comparez-la à la référence.', themes: 'Thèmes', backThemes: '← Tous les thèmes', backPhrases: '← Toutes les phrases', nextPhrase: 'Phrase suivante →', sent: 'Enregistrement envoyé. Il est dans la file de validation.', phrases: 'phrases', practice: 'Pratiquer →', listen: 'Écouter la voix de référence', record: 'Enregistrez votre voix', compare: 'Écoutez et comparez', noAudio: 'Aucun audio de référence pour cette phrase', all: 'Tous', empty: 'Aucune phrase pour ce niveau', tip: 'Parlez à votre rythme, puis écoutez votre enregistrement.', showWithoutAudio: 'Inclure les phrases sans audio', assess: 'Comparer mon rythme et mes mots', assessing: 'Analyse en cours…', scoreLabel: 'Correspondance des mots reconnus · estimation', scoreHelp: 'La hauteur naturelle de votre voix n’est pas notée.', overallLabel: 'Score total · expérimental', wordsLabel: 'Mots reconnus · Vosk', hfLabel: 'Prosodie · modèle HF', hfHelp: 'La similarité HF est brute et n’est pas une note d’accentuation syllabique.', overallHelp: 'Mots 40 % · rythme 30 % · modèle HF 30 %. Score non validé par des spécialistes.', rhythmLabel: 'Rythme et pauses · estimation', emphasisLabel: 'Relief des accents', paceLabel: 'Débit', pauseLabel: 'Pauses', rhythmHelp: 'Comparaison acoustique indicative : elle ne vérifie pas la place exacte des accents toniques.', recognized: 'Reconnu', referenceUncertain: 'La comparaison des mots est indisponible : la référence est mal reconnue.', notRecognized: 'Aucun mot reconnu. Réessayez dans un endroit calme.', assessmentError: 'Analyse du rythme ou des mots indisponible pour le moment.' },
      en: { choose: 'Choose a theme', intro: 'Choose a phrase, record your voice, then compare it with the reference.', themes: 'Themes', backThemes: '← Back to themes', backPhrases: '← Back to phrases', nextPhrase: 'Next phrase →', sent: 'Recording sent. It is now awaiting review.', phrases: 'phrases', practice: 'Practice →', listen: 'Listen to the native voice', record: 'Record your voice', compare: 'Listen and compare', noAudio: 'No reference audio for this phrase', all: 'All', empty: 'No phrases at this level', tip: 'Speak at your own pace, then listen to your recording.', showWithoutAudio: 'Include phrases without audio', assess: 'Compare my rhythm and words', assessing: 'Analyzing…', scoreLabel: 'Recognized word match · estimate', scoreHelp: 'Your natural voice pitch is not scored.', overallLabel: 'Total score · experimental', wordsLabel: 'Recognized words · Vosk', hfLabel: 'Prosody · HF model', hfHelp: 'HF similarity is raw and is not a syllable stress grade.', overallHelp: 'Words 40% · rhythm 30% · HF model 30%. Not validated by pronunciation experts.', rhythmLabel: 'Rhythm and pauses · estimate', emphasisLabel: 'Stress prominence', paceLabel: 'Pace', pauseLabel: 'Pauses', rhythmHelp: 'Indicative acoustic comparison: it does not verify the exact position of word stress.', recognized: 'Recognized', referenceUncertain: 'Word comparison is unavailable because the reference is not recognized clearly.', notRecognized: 'No words recognized. Try again in a quiet place.', assessmentError: 'Rhythm or word analysis is unavailable right now.' },
      br: { choose: 'Dibabit un tem', intro: 'Dibabit ur frazenn, enrollit ho mouezh, ha keñveriit gant ar vouezh orin goude-se.', themes: 'Temoù', backThemes: '← An holl demoù', backPhrases: '← An holl frazennoù', nextPhrase: 'Frazenn da-heul →', sent: 'Kaset eo bet an enrolladenn. Emañ o c’hortoz bezañ gwiriet.', phrases: 'frazennoù', practice: 'Pleustriñ →', listen: 'Selaouit ar vouezh orin', record: 'Enrollit ho mouezh', compare: 'Selaouit ha keñveriit', noAudio: 'N’eus ket a enrolladenn evit ar frazenn-mañ', all: 'An holl', empty: 'Frazenn ebet evit al live-mañ', tip: 'Komzit diouzh ho lusk, ha selaouit hoc’h enrolladenn.', showWithoutAudio: 'Diskouez ivez ar frazennoù hep son', assess: 'Keñveriañ ma lusk ha ma gerioù', assessing: 'O tielfennañ…', scoreLabel: 'Klotañ ar gerioù anavezet · istimadur', scoreHelp: 'N’eo ket priziet uhelder naturel ho mouezh.', overallLabel: 'Merk hollek · arnodel', wordsLabel: 'Gerioù anavezet · Vosk', hfLabel: 'Doare-komz · patrom HF', hfHelp: 'N’eo ket ar c’hlotadur HF ur merk taol-mouezh dre silabenn.', overallHelp: 'Gerioù 40 % · lusk 30 % · patrom HF 30 %. N’eo ket ur merk distagadur gwiriet.', rhythmLabel: 'Lusk ha paouezioù · istimadur', emphasisLabel: 'Kreñvder an taolioù-mouezh', paceLabel: 'Tizh', pauseLabel: 'Paouezioù', rhythmHelp: 'Keñveriadur sonel istimet : ne wiriek ket lec’h resis an taolioù-mouezh.', recognized: 'Anavezet', referenceUncertain: 'N’hall ket ar patrom anavezout ar vouezh dave a-walc’h evit reiñ ur merk fizius.', notRecognized: 'Ger ebet anavezet. Klaskit en-dro en ul lec’h sioul.', assessmentError: 'N’eo ket hegerz an dielfennadur evit poent.' },
      cy: { choose: 'Dewiswch thema', intro: 'Dewiswch frawddeg, recordiwch eich llais, yna cymharwch ef â’r cyfeirnod.', themes: 'Themâu', backThemes: '← Pob thema', backPhrases: '← Pob brawddeg', nextPhrase: 'Brawddeg nesaf →', sent: 'Anfonwyd y recordiad. Mae’n aros am adolygiad.', phrases: 'brawddeg', practice: 'Ymarfer →', listen: 'Gwrandewch ar y llais gwreiddiol', record: 'Recordiwch eich llais', compare: 'Gwrandewch a chymharwch', noAudio: 'Dim sain cyfeirio ar gyfer y frawddeg hon', all: 'Pob un', empty: 'Dim brawddegau ar y lefel hon', tip: 'Siaradwch ar eich cyflymder eich hun, yna gwrandewch ar eich recordiad.', showWithoutAudio: 'Cynnwys brawddegau heb sain', assess: 'Cymharu fy rhythm a geiriau', assessing: 'Yn dadansoddi…', scoreLabel: 'Cyfatebiaeth geiriau a adnabuwyd · amcangyfrif', scoreHelp: 'Ni chaiff traw naturiol eich llais ei sgorio.', overallLabel: 'Cyfanswm sgôr · arbrofol', wordsLabel: 'Geiriau a adnabuwyd · Vosk', hfLabel: 'Prosodi · model HF', hfHelp: 'Nid yw tebygrwydd HF yn radd pwyslais sillafau.', overallHelp: 'Geiriau 40% · rhythm 30% · model HF 30%. Nid yw hwn yn radd ynganu wedi’i dilysu.', rhythmLabel: 'Rhythm a seibiau · amcangyfrif', emphasisLabel: 'Pwyslais', paceLabel: 'Cyflymder', pauseLabel: 'Seibiau', rhythmHelp: 'Cymhariaeth sain fras: nid yw’n gwirio union leoliad y pwyslais.', recognized: 'Adnabuwyd', referenceUncertain: 'Ni all y model adnabod y cyfeirnod yn ddigon da i roi sgôr ddibynadwy.', notRecognized: 'Ni adnabuwyd geiriau. Rhowch gynnig arall mewn lle tawel.', assessmentError: 'Nid yw’r dadansoddiad ar gael ar hyn o bryd.' },
    };
    return labels[this.i18n.language()] || labels.fr;
  }

  domainCount(value: string): number {
    return this.phrases.filter((phrase) => canonicalDomain(phrase.theme) === value && this.hasReference(phrase)).length;
  }

  themeImage(value: string): string {
    const filename = this.themeImages[value];
    const version = value === 'numerique-technologies' ? '20261004-digital' : '20261004';
    return filename ? `/assets/themes/${filename}?v=${version}` : '/assets/coast-brittany.jpg';
  }

  selectDomain(value: string): void {
    this.selectedTheme = value;
    this.selectedLevel = 'all';
    this.selectedSubdomain = '';
    this.onlyWithAudio = true;
    this.currentPhrase = null;
    this.stage = 'phrases';
    this.resetRecording();
  }

  selectPhrase(phrase: Phrase): void {
    if (this.isRecording || this.submitting) return;
    this.resetRecording();
    this.currentPhrase = phrase;
    this.stage = 'practice';
  }

  backToPhrases(): void {
    if (this.isRecording || this.submitting) return;
    this.resetRecording();
    this.stage = 'phrases';
  }

  backToThemes(): void {
    if (this.isRecording || this.submitting) return;
    this.resetRecording();
    this.stage = 'themes';
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
    this.submittedRecording = false;
    this.revokeBlobUrl();
    this.lastBlob = null;
    this.durationSec = 0;

    try {
      await this.recorder.init();
      this.recorder.start();
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
      if (!blob.size) {
        this.zone.run(() => { this.error = 'L’enregistrement est vide. Réessaie après avoir vérifié le micro.'; });
        return;
      }
      this.zone.run(() => {
        this.lastBlob = blob;
        this.blobUrl = URL.createObjectURL(blob);
        this.cdr.detectChanges();
        const player = this.recordedPreview?.nativeElement;
        if (player && this.blobUrl) {
          player.src = this.blobUrl;
          player.load();
        }
      });
    } catch {
      this.clearTimer();
      this.zone.run(() => { this.error = 'Arrêt de l’enregistrement impossible.'; });
    }
  }

  async playRecorded(): Promise<void> {
    const player = this.recordedPreview?.nativeElement;
    if (!player || !this.blobUrl) return;
    if (!player.paused) {
      player.pause();
      return;
    }
    try {
      await player.play();
    } catch {
      this.error = 'Lecture de votre enregistrement impossible dans ce navigateur.';
    }
  }

  onRecordedAudioError(): void {
    if (this.blobUrl) this.error = 'Le navigateur ne parvient pas à lire cet enregistrement. Réessaie avec un autre navigateur ou micro.';
  }

  async assessPronunciation(): Promise<void> {
    const phrase = this.currentPhrase;
    const reference = this.referenceAudio;
    const recording = this.lastBlob;
    if (!phrase || !reference || !recording || this.assessing) return;
    this.assessing = true;
    this.score = null;
    this.rhythmAssessment = null;
    this.hfSimilarity = null;
    this.overallScore = null;
    this.assessmentMessage = '';
    try {
      const response = await fetch(audioFileUrl(reference.id));
      if (!response.ok) throw new Error('Reference audio unavailable');
      const audio = await response.blob();
      const rhythmResult = await firstValueFrom(this.api.compareRhythm(recording, audio, reference.id));
      this.rhythmAssessment = {
        rhythm: rhythmResult.comparison.rhythm_score,
        emphasis: rhythmResult.comparison.emphasis_score,
        pace: rhythmResult.comparison.pace_score,
        pauses: rhythmResult.comparison.pause_score,
      };
      this.hfSimilarity = rhythmResult.hf_prosody
        ? Math.round(Math.max(0, Math.min(1, rhythmResult.hf_prosody.cosine_similarity)) * 100)
        : null;
      let referenceText = this.referenceTranscripts.get(reference.id);
      if (!referenceText) {
        const result = await firstValueFrom(this.api.transcribeBreton(audio, `reference-${reference.id}.mp3`));
        referenceText = result.text;
        this.referenceTranscripts.set(reference.id, referenceText);
      }
      if (this.textSimilarity(phrase.texte, referenceText) < 0.6) {
        this.assessmentMessage = this.copy.referenceUncertain;
        return;
      }
      const result = await firstValueFrom(this.api.transcribeBreton(recording, `phrase-${phrase.id}.wav`));
      this.recognizedText = result.text.trim();
      if (!this.recognizedText) {
        this.assessmentMessage = this.copy.notRecognized;
        return;
      }
      this.score = Math.round(this.textSimilarity(phrase.texte, this.recognizedText) * 100);
      if (this.hfSimilarity !== null) {
        this.overallScore = Math.round(0.4 * this.score + 0.3 * this.rhythmAssessment.rhythm + 0.3 * this.hfSimilarity);
      }
    } catch {
      this.assessmentMessage = this.copy.assessmentError;
    } finally {
      this.assessing = false;
      this.cdr.markForCheck();
    }
  }

  private textSimilarity(expected: string, spoken: string): number {
    const normalize = (value: string) => value.toLowerCase().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '').replace(/[’']/g, '')
      .replace(/[^a-z0-9]+/g, ' ').trim();
    const left = normalize(expected);
    const right = normalize(spoken);
    if (!left || !right) return 0;
    const distance = (a: string[], b: string[]) => {
      let previous = Array.from({ length: b.length + 1 }, (_, index) => index);
      for (let i = 1; i <= a.length; i += 1) {
        const current = [i];
        for (let j = 1; j <= b.length; j += 1) {
          current[j] = Math.min(current[j - 1]! + 1, previous[j]! + 1,
            previous[j - 1]! + Number(a[i - 1] !== b[j - 1]));
        }
        previous = current;
      }
      return previous[b.length]!;
    };
    const chars = 1 - distance([...left], [...right]) / Math.max(left.length, right.length);
    const wordsLeft = left.split(' ');
    const wordsRight = right.split(' ');
    const words = 1 - distance(wordsLeft, wordsRight) / Math.max(wordsLeft.length, wordsRight.length);
    return Math.max(0, Math.min(1, 0.6 * words + 0.4 * chars));
  }

  resetRecording(): void {
    this.clearTimer();
    this.recorder.dispose();
    this.revokeBlobUrl();
    this.lastBlob = null;
    this.durationSec = 0;
    this.error = null;
    this.success = null;
    this.submittedRecording = false;
    this.score = null;
    this.rhythmAssessment = null;
    this.hfSimilarity = null;
    this.overallScore = null;
    this.recognizedText = '';
    this.assessmentMessage = '';
  }

  previousPhrase(): void {
    this.selectRelativePhrase(-1);
  }

  nextPhrase(): void {
    this.selectRelativePhrase(1);
  }

  continueAfterSubmit(): void {
    if (!this.submittedRecording) return;
    if (this.filteredPhrases.length < 2) {
      this.backToPhrases();
      return;
    }
    this.resetRecording();
    this.moveToNextPhrase();
  }

  async submitRecording(): Promise<void> {
    if (!this.currentPhrase || !this.lastBlob || this.submitting || this.assessing || this.submittedRecording) return;
    this.submitting = true;
    this.error = null;
    this.success = null;

    try {
      const recordedPhraseId = this.currentPhrase.id;
      await firstValueFrom(this.api.uploadAudio(
        this.currentPhrase.id,
        this.lastBlob,
        `phrase-${this.currentPhrase.id}.wav`,
        {
          phraseSource: 'suggested',
          domain: this.currentPhrase.theme || undefined,
          speakerRegion: this.speakerRegion || undefined,
          speakerLevel: this.speakerLevel || undefined,
        },
      ));
      this.completedPhraseIds.add(recordedPhraseId);
      this.submittedRecording = true;
      this.success = this.copy.sent;
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
      const phraseId = Number(this.route.snapshot.queryParamMap.get('phraseId') || this.currentPhrase?.id || 0);
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
        const result = await firstValueFrom(forkJoin({
          phrases: phrasesRequest,
          approved: this.api.listAudios('approved'),
        }));
        phrases = result.phrases;
        audios = result.approved;
      }

      this.phrases = this.uniquePhrases(phrases);
      this.approvedAudios = audios.filter((audio) => audio.status === 'approved');
      this.completedPhraseIds.clear();
      audios
        .filter((audio) => audio.contributor_email?.trim().toLowerCase() === userEmail)
        .forEach((audio) => this.completedPhraseIds.add(audio.phrase_id));

      const directPhrase = this.phrases.find((phrase) => phrase.id === phraseId);
      if (directPhrase) {
        this.selectedTheme = canonicalDomain(directPhrase.theme);
        this.selectedLevel = (directPhrase.niveau || '').toUpperCase() || 'all';
        this.currentPhrase = directPhrase;
        this.stage = 'practice';
      }
      if (!this.phrases.length) {
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
    const phrases = this.filteredPhrases;
    if (!this.currentPhrase || !phrases.length) return;
    const index = phrases.findIndex((phrase) => phrase.id === this.currentPhrase?.id);
    for (let offset = 1; offset <= phrases.length; offset += 1) {
      const candidate = phrases[(Math.max(index, 0) + offset) % phrases.length];
      if (!this.completedPhraseIds.has(candidate.id)) {
        this.currentPhrase = candidate;
        return;
      }
    }
    this.currentPhrase = phrases[(Math.max(index, 0) + 1) % phrases.length];
  }

  private selectRelativePhrase(offset: -1 | 1): void {
    const phrases = this.filteredPhrases;
    if (!this.currentPhrase || phrases.length < 2 || this.isRecording || this.submitting) return;
    const index = phrases.findIndex((phrase) => phrase.id === this.currentPhrase?.id);
    const nextIndex = (Math.max(index, 0) + offset + phrases.length) % phrases.length;
    this.resetRecording();
    this.currentPhrase = phrases[nextIndex];
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
