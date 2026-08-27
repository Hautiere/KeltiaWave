import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, HostListener, OnDestroy, OnInit, QueryList, ViewChild, ViewChildren, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { LearningApiService, LearningLessonDto, LearningLessonWrite, LearningProgressDto } from './learning-api.service';

type AppMode = 'learn' | 'admin';
type Screen = 'catalog' | 'intro' | 'exercise' | 'correction' | 'result' | 'progression' | 'profiles';
type ResultTab = 'result' | 'translation' | 'vocabulary' | 'grammar';
type TokenKind = 'word' | 'space' | 'punctuation';
type UiLanguage = 'fr' | 'br' | 'en';

interface Blank { id: string; answer: string; accepted: string[]; acceptMutations: boolean; start: number; end: number; value: string; }
interface PlayerPart { text?: string; blank?: Blank; }
interface LessonSegment { id: number; start: number; end: number; parts: PlayerPart[]; translation?: string; }
interface VocabularyItem { word: string; translation: string; example: string; }
interface GrammarItem { title: string; explanation: string; example: string; translation: string; }
interface Lesson { title: string; level: string; duration: string; theme: string; description: string; segments: LessonSegment[]; vocabulary: VocabularyItem[]; grammar: GrammarItem[]; }
interface AdminToken { id: string; text: string; kind: TokenKind; selected: boolean; acceptedVariants: string; acceptMutations: boolean; }
interface AdminSegment { id: number; start: number; end: number; tokens: AdminToken[]; translation: string; }
interface CatalogLesson { id?: number; title: string; level: string; theme: string; duration: string; durationSeconds: number | null; questions: number; status: string; progress: number; visual: string; thumbnail?: string; source?: LearningLessonDto; }
interface StoredProgress { lessonId: number; status: 'started' | 'completed'; bestScore: number; totalQuestions: number; attempts: number; updatedAt: string; }

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class AppComponent implements AfterViewInit, OnDestroy, OnInit {
  readonly api = inject(LearningApiService);
  @ViewChild('lessonVideo') private lessonVideo?: ElementRef<HTMLMediaElement>;
  @ViewChild('videoShell') private videoShell?: ElementRef<HTMLElement>;
  @ViewChild('mediaCard') private mediaCard?: ElementRef<HTMLElement>;
  @ViewChild('transcriptScroll') private transcriptScroll?: ElementRef<HTMLElement>;
  @ViewChildren('transcriptSegment') private transcriptSegmentElements?: QueryList<ElementRef<HTMLElement>>;
  @ViewChild('translationScroll') private translationScroll?: ElementRef<HTMLElement>;
  @ViewChildren('translationSegment') private translationSegmentElements?: QueryList<ElementRef<HTMLElement>>;
  @ViewChild('adminPreviewScroll') private adminPreviewScroll?: ElementRef<HTMLElement>;
  @ViewChildren('adminPreviewSegment') private adminPreviewSegmentElements?: QueryList<ElementRef<HTMLElement>>;

  readonly levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
  readonly testProfiles = [
    { label: 'Élève', name: 'Mael Le Gall', role: 'Utilisateur', email: 'tiar1@keltia.test', password: 'classe123', description: 'Teste une progression apprenant synchronisée.', tone: 'student' },
    { label: 'Admin', name: 'Admin Learning', role: 'Administrateur', email: 'learning.admin@keltia.test', password: 'classe123', description: 'Teste la création et la modification des leçons.', tone: 'admin' },
  ];
  uiLanguage: UiLanguage = (localStorage.getItem('keltiaLearn.language') as UiLanguage) || 'fr';
  private readonly uiText: Record<UiLanguage, Record<string, string>> = {
    fr: { lessons: 'Leçons', admin: 'Administration', progress: 'Progression', signin: 'Sign in', signout: 'Sign out', profiles: 'Profils de test', heroTitle: '🎧 Écouter & comprendre', heroCopy: 'Plongez dans le breton à travers des vidéos et des jeux interactifs.', search: 'Rechercher une leçon, un thème ou un mot-clé…', filters: 'Filtres', theme: 'Thème', allThemes: 'Tous les thèmes', level: 'Niveau CECRL', allLevels: 'Tous les niveaux', duration: 'Durée', allDurations: 'Toutes les durées', gameType: 'Type de jeu', gaps: 'Texte à trous', reset: 'Réinitialiser', grid: 'Affichage en grille', noLesson: 'Aucune leçon ne correspond à ces filtres.', accountHelp: 'Utilise ton compte KeltiaWave.', email: 'Adresse électronique', password: 'Mot de passe', optional: 'La connexion est facultative pour suivre une leçon.', myProgress: 'Ma progression', connectedUser: 'Utilisateur connecté', administrator: 'Administrateur', testTitle: 'Profils de test', testCopy: 'Choisis un profil pour tester immédiatement le parcours utilisateur ou administrateur.', useProfile: 'Utiliser ce profil', backLessons: 'Retour aux leçons', lesson: 'Leçon', listen: 'Écoute', correction: 'Correction', result: 'Résultat', start: 'Commencer', questions: 'Questions', words: 'mots', instruction: 'Regarde la vidéo et complète les mots manquants.', startedLessons: 'Leçons commencées', completedLessons: 'Leçons terminées', continue: 'Continuer', restart: 'Recommencer', noProgress: 'Aucune leçon commencée. Tu peux choisir librement une leçon sans te connecter.' },
    br: { lessons: 'Kentelioù', admin: 'Melestradurezh', progress: 'Araokadur', signin: 'Kevreañ', signout: 'Digevreañ', profiles: 'Profiloù amprouiñ', heroTitle: '🎧 Selaou & kompren', heroCopy: 'Splujit er brezhoneg dre videoioù ha c’hoarioù etregwezhiat.', search: 'Klask ur gentel, un dodenn pe ur ger…', filters: 'Siloù', theme: 'Dodenn', allThemes: 'An holl dodennoù', level: 'Live CEFR', allLevels: 'An holl liveoù', duration: 'Padelezh', allDurations: 'An holl badelezhoù', gameType: 'Doare c’hoari', gaps: 'Testenn da glokaat', reset: 'Adderaouekaat', grid: 'Skrammañ e kael', noLesson: 'Kentel ebet evit ar siloù-mañ.', accountHelp: 'Implijit ho kont KeltiaWave.', email: 'Chomlec’h postel', password: 'Ger-tremen', optional: 'N’eo ket ret kevreañ evit heuliañ ur gentel.', myProgress: 'Ma araokadur', connectedUser: 'Implijer kevreet', administrator: 'Merour', testTitle: 'Profiloù amprouiñ', testCopy: 'Dibabit ur profil evit amprouiñ hent an implijer pe ar merour.', useProfile: 'Implij ar profil-mañ', backLessons: 'Distreiñ d’ar c’hentelioù', lesson: 'Kentel', listen: 'Selaou', correction: 'Reizhadenn', result: 'Disoc’h', start: 'Kregiñ', questions: 'Goulennoù', words: 'ger', instruction: 'Sellit ouzh ar video ha klokait ar gerioù a vank.', startedLessons: 'Kentelioù kroget', completedLessons: 'Kentelioù echuet', continue: 'Kenderc’hel', restart: 'Adkregiñ', noProgress: 'Kentel ebet kroget. Gallout a rit dibab ur gentel hep kevreañ.' },
    en: { lessons: 'Lessons', admin: 'Administration', progress: 'Progress', signin: 'Sign in', signout: 'Sign out', profiles: 'Test profiles', heroTitle: '🎧 Listen & understand', heroCopy: 'Immerse yourself in Breton through videos and interactive games.', search: 'Search for a lesson, topic or keyword…', filters: 'Filters', theme: 'Topic', allThemes: 'All topics', level: 'CEFR level', allLevels: 'All levels', duration: 'Duration', allDurations: 'All durations', gameType: 'Game type', gaps: 'Fill in the blanks', reset: 'Reset', grid: 'Grid view', noLesson: 'No lesson matches these filters.', accountHelp: 'Use your KeltiaWave account.', email: 'Email address', password: 'Password', optional: 'Signing in is optional to take a lesson.', myProgress: 'My progress', connectedUser: 'Signed-in user', administrator: 'Administrator', testTitle: 'Test profiles', testCopy: 'Choose a profile to immediately test the learner or administrator journey.', useProfile: 'Use this profile', backLessons: 'Back to lessons', lesson: 'Lesson', listen: 'Listen', correction: 'Correction', result: 'Result', start: 'Start', questions: 'Questions', words: 'words', instruction: 'Watch the video and fill in the missing words.', startedLessons: 'Lessons started', completedLessons: 'Lessons completed', continue: 'Continue', restart: 'Restart', noProgress: 'No lesson started. You can choose any lesson without signing in.' },
  };
  readonly demoCatalogLessons: CatalogLesson[] = [
    { title: 'An amzer e Breizh', level: 'A2', theme: 'Vie quotidienne', duration: '8:43', durationSeconds: 523, questions: 8, status: 'Nouveau', progress: 0, visual: 'coast' },
    { title: 'Ar mor hag an aod', level: 'A2', theme: 'Culture', duration: '9:12', durationSeconds: 552, questions: 10, status: 'En cours · 60 %', progress: 60, visual: 'town' },
    { title: 'Sonerezh Breizh', level: 'A2', theme: 'Culture', duration: '7:56', durationSeconds: 476, questions: 9, status: 'Nouveau', progress: 0, visual: 'music' },
    { title: 'Etre an dud', level: 'A1', theme: 'Vie quotidienne', duration: '9:05', durationSeconds: 545, questions: 12, status: 'En cours · 25 %', progress: 25, visual: 'market' },
    { title: 'Broioù Breizh', level: 'B1', theme: 'Géographie', duration: '8:17', durationSeconds: 497, questions: 9, status: 'Terminé ✓', progress: 100, visual: 'country' },
    { title: 'An amzer', level: 'A2', theme: 'Vie quotidienne', duration: '6:34', durationSeconds: 394, questions: 7, status: 'Terminé ✓', progress: 100, visual: 'weather' },
    { title: 'Istor Breizh', level: 'B1', theme: 'Histoire', duration: '10:28', durationSeconds: 628, questions: 15, status: 'Nouveau', progress: 0, visual: 'history' },
    { title: 'Ar vuhez gant ar mor', level: 'A2', theme: 'Culture', duration: '8:59', durationSeconds: 539, questions: 11, status: 'Terminé ✓', progress: 100, visual: 'harbor' },
  ];
  catalogLessons: CatalogLesson[] = [...this.demoCatalogLessons];
  readonly demoLesson: Lesson = {
    title: 'An amzer e Breizh', level: 'A2', duration: '2 min 15', theme: 'Vie quotidienne',
    description: 'Un reportage court sur la météo et le littoral en Bretagne.',
    segments: [
      { id: 1, start: 24, end: 31, parts: [{ text: "Demat deoc’h. Hiziv ez eo brav an amzer." }], translation: 'Bonjour à vous. Aujourd’hui, il fait beau.' },
      { id: 2, start: 32, end: 39, parts: [{ text: 'Mont a ran da ' }, { blank: this.blank('demo-kemper', 'Kemper', ['Quimper'], 32, 39) }, { text: ' evit gwelet ar mor.' }], translation: 'Je vais à Quimper pour voir la mer.' },
      { id: 3, start: 44, end: 51, parts: [{ text: "Bez’ ez eus kalz a dud war an " }, { blank: this.blank('demo-aod', 'aod', [], 44, 51) }, { text: '.' }], translation: 'Il y a beaucoup de monde sur la côte.' },
    ],
    vocabulary: [{ word: 'amzer', translation: 'temps, météo', example: 'Brav eo an amzer.' }, { word: 'mor', translation: 'mer', example: 'Gwelet ar mor.' }, { word: 'aod', translation: 'côte, rivage', example: 'War an aod.' }],
    grammar: [{ title: 'Mont a ran da + lieu', explanation: 'Cette construction permet d’exprimer un déplacement vers un lieu.', example: 'Mont a ran da Gemper.', translation: 'Je vais à Quimper.' }],
  };

  mode: AppMode = 'learn';
  screen: Screen = 'catalog';
  resultTab: ResultTab = 'result';
  catalogSearch = '';
  catalogLevel = 'Tous';
  catalogTheme = 'Tous';
  catalogDuration = 'Toutes';
  activeLesson: Lesson = this.demoLesson;
  activeCatalogLesson: CatalogLesson | null = null;
  historicalProgress: StoredProgress | null = null;
  progressRecords: StoredProgress[] = [];
  learnerEmail = '';
  learnerPassword = '';
  learnerMessage = '';
  learnerBusy = false;
  accountOpen = false;
  manualLoginOpen = false;
  exercisePage = 0;
  videoUrl = '';
  videoName = '';
  videoFile: File | null = null;
  videoDurationSeconds: number | null = null;
  activeMediaIsAudio = false;
  activeCoverUrl = '';
  activeSourceUrl = '';
  activeSourceLinkLabel = '';
  coverFile: File | null = null;
  coverPreviewUrl = '';
  uploadedCoverName = '';
  playerPanelHeight = 0;
  resultPanelHeight = 0;
  currentVideoTime = 0;
  subtitleLanguage: 'off' | 'br' | 'fr' = 'off';
  replayingId = '';
  private replayTimer?: number;
  private transcriptParsingTimer?: number;
  private panelResizeObserver?: ResizeObserver;
  private lastCenteredSegmentId: number | null = null;
  private lastAdminCenteredSegmentId: number | null = null;

  adminTitle = 'An amzer e Breizh';
  adminLevel = 'A2';
  adminTheme = 'Vie quotidienne';
  adminDescription = 'Un reportage court sur la météo et le littoral en Bretagne.';
  adminDuration = '';
  adminSourceUrl = '';
  adminSourceLinkLabel = '';
  transcriptText = '';
  transcriptFileName = '';
  adminSegments: AdminSegment[] = [];
  adminVocabulary: VocabularyItem[] = [];
  adminGrammar: GrammarItem = { title: '', explanation: '', example: '', translation: '' };
  adminMessage = '';
  adminError = '';
  adminEmail = '';
  adminPassword = '';
  adminBusy = false;
  backendAvailable = true;
  currentLessonId: number | null = null;
  uploadedVideoName = '';
  adminLessons: LearningLessonDto[] = [];

  get blanks(): Blank[] {
    return this.activeLesson.segments.flatMap((segment) => segment.parts.flatMap((part) => part.blank ? [part.blank] : []));
  }

  get selectedAdminTokens(): AdminToken[] {
    return this.adminSegments.flatMap((segment) => segment.tokens.filter((token) => token.selected));
  }

  get score(): number { return this.blanks.filter((blank) => this.isCorrect(blank)).length; }
  get displayedScore(): number { return this.historicalProgress?.bestScore ?? this.score; }
  get displayedTotalQuestions(): number { return this.historicalProgress?.totalQuestions || this.blanks.length; }
  get displayedScorePercent(): number { return this.historicalProgress ? this.progressScore(this.historicalProgress) : this.scorePercent; }
  t(key: string): string {
    if (key === 'heroTitle') return ({ fr: 'Regarder. Écouter. Play.', br: 'Sellit. Selaouit. C’hoariit.', en: 'Watch. Listen. Play.' })[this.uiLanguage];
    if (key === 'sourceOriginal') return ({ fr: 'Aller sur l’original', br: 'Mont d’an orin', en: 'Go to the original' })[this.uiLanguage];
    const extra: Record<string, Record<UiLanguage, string>> = {
      translation: { fr: 'Traduction', br: 'Troidigezh', en: 'Translation' },
      vocabulary: { fr: 'Vocabulaire', br: 'Geriaoueg', en: 'Vocabulary' },
      grammar: { fr: 'Grammaire', br: 'Yezhadur', en: 'Grammar' },
      mediaPlayed: { fr: 'Média lu', br: 'Media lennet', en: 'Media played' },
      exerciseCompleted: { fr: 'Exercice terminé', br: 'Poelladenn echuet', en: 'Exercise completed' },
      explanation: { fr: 'Explication', br: 'Displegadenn', en: 'Explanation' },
      example: { fr: 'Exemple', br: 'Skouer', en: 'Example' },
      addWord: { fr: 'Ajouter un mot', br: 'Ouzhpennañ ur ger', en: 'Add a word' },
      bretonWord: { fr: 'Mot breton', br: 'Ger brezhoneg', en: 'Breton word' },
    };
    if (extra[key]) return extra[key][this.uiLanguage];
    return this.uiText[this.uiLanguage][key] ?? key;
  }
  adminT(key: string): string {
    if (key === 'transcriptionHelp') return ({ fr: 'Importe un fichier TXT, SRT ou VTT, puis corrige chaque bloc avec la vidéo.', br: 'Enporzh ur restr TXT, SRT pe VTT, ha reizhañ pep bloc’h gant ar video.', en: 'Import a TXT, SRT or VTT file, then edit each block alongside the video.' })[this.uiLanguage];
    const copy: Record<UiLanguage, Record<string, string>> = {
      fr: { heading: 'Nouvel exercice', intro: 'Prépare, enregistre et publie une leçon sur le serveur KeltiaWave.', saved: 'Leçons enregistrées', savedHelp: 'Rouvre un brouillon ou une leçon publiée pour la corriger.', newLesson: 'Nouvelle leçon', noSaved: 'Aucune leçon enregistrée.', media: 'Média et leçon', editLesson: 'Modifier la leçon', editHelp: 'Les changements seront enregistrés dans la leçon existante.', uploadHelp: 'Le média sera envoyé au stockage lors de la sauvegarde.', title: 'Titre', level: 'Niveau', theme: 'Thème', description: 'Description', mediaDuration: 'Durée du média', durationHelp: 'Détectée automatiquement, mais modifiable.', sourceUrl: 'URL de la source originale', sourceHelp: 'Lien facultatif affiché près du lecteur.', sourceLabel: 'Texte du lien vers l’original', sourceLabelHelp: 'Facultatif. Si ce champ est vide, le texte est traduit automatiquement.', chooseMedia: 'Choisir une vidéo ou un fichier audio', chooseCover: 'Choisir une jaquette', transcription: 'Transcription', transcriptionHelp: 'Importe TXT, SRT ou VTT, ou colle directement le texte.', importTranscript: 'Importer une transcription', textSubtitles: 'Texte ou sous-titres', adjustText: 'Réajuster le texte', createGaps: 'Créer les trous', createGapsHelp: 'Clique sur un mot pour le masquer. La ponctuation reste affichée.', preview: 'Aperçu de l’exercice', translations: 'Traductions', vocabulary: 'Vocabulaire', grammar: 'Grammaire', export: 'Exporter le JSON', playerPreview: 'Aperçu joueur', saveDraft: 'Enregistrer le brouillon', publish: 'Publier', sending: 'Envoi…', signout: 'Se déconnecter' },
      br: { heading: 'Poelladenn nevez', intro: 'Prientiñ, enrollañ hag embann ur gentel war servijer KeltiaWave.', saved: 'Kentelioù enrollet', savedHelp: 'Digor ur brouilhed pe ur gentel embannet evit reizhañ anezhi.', newLesson: 'Kentel nevez', noSaved: 'Kentel enrollet ebet.', media: 'Media ha kentel', editLesson: 'Kemmañ ar gentel', editHelp: 'Enrollet e vo ar c’hemmoù er gentel-mañ.', uploadHelp: 'Kaset e vo ar media d’ar stokañ pa vo enrollet.', title: 'Titl', level: 'Live', theme: 'Dodenn', description: 'Deskrivadur', mediaDuration: 'Padelezh ar media', durationHelp: 'Dinoet ent emgefre, met kemmus.', sourceUrl: 'URL ar vammenn orin', sourceHelp: 'Liamm diret diskouezet e-kichen al lenner.', sourceLabel: 'Testenn al liamm d’an orin', sourceLabelHelp: 'Diret. Ma vez goullo e vo troet ent emgefre.', chooseMedia: 'Dibab ur video pe ur restr audio', chooseCover: 'Dibab ur golo', transcription: 'Treuzskrivadur', transcriptionHelp: 'Enporzh TXT, SRT pe VTT, pe pegañ an destenn.', importTranscript: 'Enporzh un treuzskrivadur', textSubtitles: 'Testenn pe istitloù', adjustText: 'Adkempenn an destenn', createGaps: 'Krouiñ ar c’hlokaennoù', createGapsHelp: 'Klikit war ur ger evit kuzhat anezhañ. Diskouezet e chom ar poentadur.', preview: 'Rakwelet ar boelladenn', translations: 'Troidigezhioù', vocabulary: 'Geriaoueg', grammar: 'Yezhadur', export: 'Ezporzhiañ JSON', playerPreview: 'Rakwelet evel c’hoarier', saveDraft: 'Enrollañ ar brouilhed', publish: 'Embann', sending: 'O kas…', signout: 'Digevreañ' },
      en: { heading: 'New exercise', intro: 'Prepare, save and publish a lesson on the KeltiaWave server.', saved: 'Saved lessons', savedHelp: 'Reopen a draft or published lesson to edit it.', newLesson: 'New lesson', noSaved: 'No saved lessons.', media: 'Media and lesson', editLesson: 'Edit lesson', editHelp: 'Changes will be saved to the existing lesson.', uploadHelp: 'The media will be uploaded to storage when you save.', title: 'Title', level: 'Level', theme: 'Topic', description: 'Description', mediaDuration: 'Media duration', durationHelp: 'Detected automatically, but editable.', sourceUrl: 'Original source URL', sourceHelp: 'Optional link displayed next to the player.', sourceLabel: 'Original link text', sourceLabelHelp: 'Optional. When empty, the text is translated automatically.', chooseMedia: 'Choose a video or audio file', chooseCover: 'Choose a cover image', transcription: 'Transcript', transcriptionHelp: 'Import TXT, SRT or VTT, or paste the text directly.', importTranscript: 'Import a transcript', textSubtitles: 'Text or subtitles', adjustText: 'Readjust text', createGaps: 'Create blanks', createGapsHelp: 'Click a word to hide it. Punctuation remains visible.', preview: 'Exercise preview', translations: 'Translations', vocabulary: 'Vocabulary', grammar: 'Grammar', export: 'Export JSON', playerPreview: 'Learner preview', saveDraft: 'Save draft', publish: 'Publish', sending: 'Sending…', signout: 'Sign out' },
    };
    return copy[this.uiLanguage][key] ?? this.t(key);
  }
  scoreAppreciation(): string {
    const percent = this.displayedScorePercent;
    const messages = {
      fr: percent >= 90 ? 'Excellent travail !' : percent >= 70 ? 'Très bon résultat !' : percent >= 50 ? 'Bien joué, continue !' : 'Un bon début, continue à progresser !',
      br: percent >= 90 ? 'Labour dispar !' : percent >= 70 ? 'Disoc’h mat-tre !' : percent >= 50 ? 'Brav, kendalc’hit !' : 'Un deroù mat, kendalc’hit da vont war-raok !',
      en: percent >= 90 ? 'Excellent work!' : percent >= 70 ? 'Very good result!' : percent >= 50 ? 'Well done, keep going!' : 'A good start—keep progressing!',
    };
    return messages[this.uiLanguage];
  }
  changeLanguage(language: UiLanguage): void { this.uiLanguage = language; localStorage.setItem('keltiaLearn.language', language); }
  get completedProgressCount(): number { return this.progressRecords.filter((record) => record.status === 'completed').length; }
  get scorePercent(): number { return this.blanks.length ? Math.round((this.score / this.blanks.length) * 100) : 0; }
  get maxPageTextWeight(): number {
    if (window.innerWidth <= 520) return 90;
    if (window.innerWidth <= 820) return 130;
    if (window.innerWidth <= 1400) return 170;
    return 220;
  }
  get exercisePages(): LessonSegment[][] {
    return [this.activeLesson.segments];
  }
  get exercisePageCount(): number { return this.exercisePages.length; }
  get exercisePageIndexes(): number[] { return Array.from({ length: this.exercisePageCount }, (_, index) => index); }
  get visibleSegments(): LessonSegment[] {
    return this.exercisePages[this.exercisePage] ?? [];
  }
  get visibleBlanks(): Blank[] {
    return this.visibleSegments.flatMap((segment) => segment.parts.flatMap((part) => part.blank ? [part.blank] : []));
  }
  get currentSubtitleSegments(): LessonSegment[] {
    return this.activeLesson.segments.filter((segment) => this.currentVideoTime >= segment.start && this.currentVideoTime <= segment.end);
  }
  get currentAdminSubtitleSegments(): AdminSegment[] {
    return this.adminSegments.filter((segment) => this.currentVideoTime >= segment.start && this.currentVideoTime <= segment.end);
  }
  get hasFrenchSubtitles(): boolean { return this.activeLesson.segments.some((segment) => !!segment.translation?.trim()); }
  get translationWindow(): Array<LessonSegment | null> {
    const segments = this.activeLesson.segments;
    if (!segments.length) return [null, null, null];
    const activeIndex = Math.max(0, segments.findIndex((segment) => this.isSegmentActive(segment)));
    return [segments[activeIndex - 1] ?? null, segments[activeIndex], segments[activeIndex + 1] ?? null];
  }
  isSegmentActive(segment: LessonSegment): boolean {
    const synchronized = this.activeLesson.segments.find((item) => this.currentVideoTime >= item.start && this.currentVideoTime <= item.end)
      ?? this.activeLesson.segments.find((item) => item.start > this.currentVideoTime)
      ?? this.activeLesson.segments.at(-1);
    return synchronized?.id === segment.id;
  }
  get catalogThemes(): string[] { return ['Tous', ...new Set(this.catalogLessons.map((lesson) => lesson.theme))]; }
  get filteredCatalogLessons(): CatalogLesson[] {
    const query = this.normalize(this.catalogSearch);
    return this.catalogLessons.filter((lesson) =>
      (this.catalogLevel === 'Tous' || lesson.level === this.catalogLevel) &&
      (this.catalogTheme === 'Tous' || lesson.theme === this.catalogTheme) &&
      (this.catalogDuration === 'Toutes' || (lesson.durationSeconds !== null && (
        (this.catalogDuration === 'Courte' && lesson.durationSeconds <= 180) ||
        (this.catalogDuration === 'Moyenne' && lesson.durationSeconds > 180 && lesson.durationSeconds <= 600) ||
        (this.catalogDuration === 'Longue' && lesson.durationSeconds > 600)
      ))) &&
      (!query || this.normalize(`${lesson.title} ${lesson.theme} ${lesson.level}`).includes(query))
    );
  }
  progressLesson(record: StoredProgress): CatalogLesson | undefined { return this.catalogLessons.find((lesson) => lesson.id === record.lessonId); }
  progressScore(record: StoredProgress): number { return record.totalQuestions ? Math.round(record.bestScore * 100 / record.totalQuestions) : 0; }

  @HostListener('window:popstate')
  syncModeFromUrl(): void { this.mode = window.location.pathname.startsWith('/admin') && this.api.user()?.role === 'admin' ? 'admin' : 'learn'; }

  @HostListener('window:resize')
  syncPlayerHeight(): void {
    const videoHeight = this.videoShell?.nativeElement.getBoundingClientRect().height ?? 0;
    this.playerPanelHeight = videoHeight ? Math.ceil(videoHeight + 2) : 0;
    this.resultPanelHeight = this.mediaCard?.nativeElement.getBoundingClientRect().height ?? 0;
    this.exercisePage = Math.min(this.exercisePage, this.exercisePageCount - 1);
  }

  @HostListener('document:click')
  closeAccountMenu(): void { this.accountOpen = false; }

  @HostListener('document:keydown.escape')
  closeAccountMenuWithEscape(): void { this.accountOpen = false; }

  ngOnInit(): void {
    this.loadLocalProgress();
    this.loadCatalog();
    if (this.api.token()) {
      this.api.me().subscribe({
        next: (user) => { if (user.role === 'admin') { this.loadAdminLessons(); if (window.location.pathname.startsWith('/admin')) this.mode = 'admin'; } this.loadProgress(); },
        error: () => this.api.logout(),
      });
    }
  }

  ngAfterViewInit(): void {
    this.panelResizeObserver = new ResizeObserver(() => this.syncPlayerHeight());
    if (this.videoShell) this.panelResizeObserver.observe(this.videoShell.nativeElement);
    if (this.mediaCard) this.panelResizeObserver.observe(this.mediaCard.nativeElement);
    this.syncPlayerHeight();
  }

  navigate(mode: AppMode): void {
    if (mode === 'admin' && this.api.user()?.role !== 'admin') { this.accountOpen = true; return; }
    this.mode = mode;
    window.history.pushState({}, '', mode === 'admin' ? '/admin' : '/');
    if (mode === 'learn') this.screen = 'catalog';
  }

  openTestProfiles(): void { this.accountOpen = false; this.mode = 'learn'; this.screen = 'profiles'; }

  async loginTestProfile(profile: { email: string; password: string }): Promise<void> {
    this.learnerEmail = profile.email; this.learnerPassword = profile.password;
    await this.loginFromHeader();
  }

  openProgression(): void {
    this.mode = 'learn';
    this.screen = 'progression';
    this.loadProgress();
  }

  async loginLearner(): Promise<void> {
    this.learnerMessage = ''; this.learnerBusy = true;
    try {
      await firstValueFrom(this.api.login(this.learnerEmail.trim(), this.learnerPassword));
      this.learnerPassword = '';
      try { await this.syncLocalProgressToServer(); } catch { /* La connexion reste valide si une ancienne progression locale ne peut pas être fusionnée. */ }
      this.loadProgress();
      this.learnerMessage = 'Connexion réussie. Ta progression est maintenant synchronisée.';
    } catch (error) {
      this.learnerMessage = this.apiError(error, 'Connexion impossible.');
    } finally {
      this.learnerBusy = false;
    }
  }

  async loginFromHeader(): Promise<void> {
    this.learnerMessage = ''; this.learnerBusy = true;
    try {
      const response = await firstValueFrom(this.api.login(this.learnerEmail.trim(), this.learnerPassword));
      this.learnerPassword = '';
      try { await this.syncLocalProgressToServer(); } catch { /* Synchronisation non bloquante. */ }
      this.loadProgress();
      if (response.user.role === 'admin') {
        this.loadAdminLessons();
        this.navigate('admin');
      } else if (this.mode === 'admin') {
        this.navigate('learn');
      } else if (this.screen === 'profiles') {
        this.openProgression();
      }
      this.accountOpen = false;
    } catch (error) {
      this.learnerMessage = this.apiError(error, 'Identifiants incorrects ou connexion impossible.');
    } finally {
      this.learnerBusy = false;
    }
  }

  signOut(): void {
    this.api.logout();
    this.accountOpen = false;
    this.loadLocalProgress();
    this.applyProgressToCatalog();
    this.navigate('learn');
  }

  openCatalogLesson(lesson: CatalogLesson): void {
    this.historicalProgress = null;
    this.activeCatalogLesson = lesson;
    this.activeLesson = lesson.source ? this.lessonFromApi(lesson.source) : { ...this.demoLesson, title: lesson.title, level: lesson.level, theme: lesson.theme, duration: lesson.duration };
    this.activeMediaIsAudio = lesson.source?.videos[0]?.content_type.startsWith('audio/') ?? false;
    this.activeCoverUrl = lesson.thumbnail ?? '';
    this.activeSourceUrl = lesson.source?.videos[0]?.source_url ?? '';
    this.activeSourceLinkLabel = lesson.source?.videos[0]?.source_link_label ?? '';
    if (lesson.source?.videos[0]) {
      this.setVideoUrl(this.api.mediaUrl(lesson.source.videos[0].id), lesson.source.videos[0].original_filename);
    } else if (lesson.source) {
      this.setVideoUrl('', '');
    }
    this.screen = 'intro';
  }

  openProgressDetail(record: StoredProgress, tab: ResultTab): void {
    const lesson = this.progressLesson(record);
    if (!lesson) return;
    this.activeCatalogLesson = lesson;
    this.activeLesson = lesson.source ? this.lessonFromApi(lesson.source) : { ...this.demoLesson, title: lesson.title, level: lesson.level, theme: lesson.theme, duration: lesson.duration };
    this.activeMediaIsAudio = lesson.source?.videos[0]?.content_type.startsWith('audio/') ?? false;
    this.activeCoverUrl = lesson.thumbnail ?? '';
    this.activeSourceUrl = lesson.source?.videos[0]?.source_url ?? '';
    this.activeSourceLinkLabel = lesson.source?.videos[0]?.source_link_label ?? '';
    this.historicalProgress = record;
    this.resultTab = tab;
    this.subtitleLanguage = 'off';
    if (lesson.source?.videos[0]) this.setVideoUrl(this.api.mediaUrl(lesson.source.videos[0].id), lesson.source.videos[0].original_filename);
    else this.setVideoUrl('', '');
    this.screen = 'result';
    this.schedulePlayerHeightSync();
    if (tab === 'translation') {
      const active = this.activeLesson.segments.find((segment) => this.isSegmentActive(segment)) ?? this.activeLesson.segments[0];
      if (active) window.requestAnimationFrame(() => window.requestAnimationFrame(() => this.centerActiveTranslationSegment(active.id, false)));
    }
  }

  startLesson(): void {
    if (!this.beginLesson()) return;
    void this.lessonVideo?.nativeElement.play();
  }

  handleVideoPlay(): void {
    if (this.screen === 'intro') this.beginLesson();
  }

  selectVideo(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.videoFile = file;
    this.activeMediaIsAudio = file.type.startsWith('audio/') || file.name.toLowerCase().endsWith('.mp3');
    if (this.activeMediaIsAudio) this.activeCoverUrl = this.coverPreviewUrl;
    this.videoDurationSeconds = null;
    this.uploadedVideoName = '';
    if (this.videoUrl) URL.revokeObjectURL(this.videoUrl);
    this.videoUrl = URL.createObjectURL(file);
    this.videoName = file.name;
    queueMicrotask(() => { this.lessonVideo?.nativeElement.load(); this.schedulePlayerHeightSync(); });
  }

  selectCover(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.coverFile = file;
    this.uploadedCoverName = '';
    this.setCoverPreview(URL.createObjectURL(file));
    this.activeCoverUrl = this.coverPreviewUrl;
  }

  videoMetadataLoaded(): void {
    this.syncPlayerHeight();
    const duration = this.lessonVideo?.nativeElement.duration;
    this.videoDurationSeconds = duration && Number.isFinite(duration) ? Math.round(duration) : null;
    if (this.mode === 'admin' && this.videoDurationSeconds !== null) this.adminDuration = this.formatTime(this.videoDurationSeconds);
    const activeSegment = this.activeLesson.segments.find((segment) => this.currentVideoTime >= segment.start && this.currentVideoTime <= segment.end);
    if (activeSegment) queueMicrotask(() => this.centerActiveTranscriptSegment(activeSegment.id, false));
  }

  seekMedia(event: Event): void {
    const media = this.lessonVideo?.nativeElement;
    if (!media) return;
    const target = Number((event.target as HTMLInputElement).value);
    if (!Number.isFinite(target)) return;
    media.currentTime = target;
    this.currentVideoTime = target;
  }

  syncAdminPreview(event: Event): void {
    this.currentVideoTime = (event.currentTarget as HTMLMediaElement).currentTime;
    const active = this.currentAdminSubtitleSegments[0];
    if (active && active.id !== this.lastAdminCenteredSegmentId) {
      this.lastAdminCenteredSegmentId = active.id;
      queueMicrotask(() => this.centerActiveAdminPreviewSegment(active.id));
    }
  }

  updateAdminSegmentText(segment: AdminSegment, text: string): void {
    const selectedWords = new Map(segment.tokens.filter((token) => token.selected).map((token) => [this.normalize(token.text), token]));
    segment.tokens = this.tokenize(text, segment.id);
    for (const token of segment.tokens) this.restoreTokenOptions(token, selectedWords.get(this.normalize(token.text)));
    this.syncTranscriptFromAdminBlocks();
  }

  syncTranscriptFromAdminBlocks(): void {
    this.transcriptText = this.serializeAdminTranscript();
  }

  updateAdminSegmentEnd(index: number, value: number | string): void {
    const end = Number(value);
    if (!Number.isFinite(end)) return;
    this.adminSegments[index].end = end;
    const next = this.adminSegments[index + 1];
    if (next) next.start = end;
    this.syncTranscriptFromAdminBlocks();
  }

  async loginAdmin(): Promise<void> {
    this.adminError = ''; this.adminMessage = ''; this.adminBusy = true;
    try {
      const response = await firstValueFrom(this.api.login(this.adminEmail.trim(), this.adminPassword));
      this.adminPassword = '';
      if (response.user.role !== 'admin') {
        this.api.logout();
        this.adminError = 'Ce compte ne possède pas le rôle administrateur.';
        return;
      }
      this.adminMessage = `Connecté en tant que ${response.user.display_name}.`;
      this.loadAdminLessons();
    } catch (error) {
      this.adminError = this.apiError(error, 'Connexion impossible.');
    } finally {
      this.adminBusy = false;
    }
  }

  async saveAdminLesson(publish: boolean): Promise<void> {
    this.adminError = ''; this.adminMessage = '';
    if (this.api.user()?.role !== 'admin') { this.adminError = 'Connecte-toi avec un compte administrateur.'; return; }
    if (!this.adminSegments.length || !this.selectedAdminTokens.length) { this.adminError = 'Ajoute une transcription et sélectionne au moins un mot.'; return; }
    if (!this.videoFile && !this.uploadedVideoName) { this.adminError = 'Ajoute une vidéo ou un MP3 avant la sauvegarde.'; return; }
    const durationSeconds = this.manualDurationSeconds();
    if (this.adminDuration.trim() && durationSeconds === null) { this.adminError = 'La durée doit être saisie en secondes ou au format mm:ss.'; return; }

    this.adminBusy = true;
    try {
      const payload = this.adminLessonPayload();
      const saved = this.currentLessonId === null
        ? await firstValueFrom(this.api.createLesson(payload))
        : await firstValueFrom(this.api.updateLesson(this.currentLessonId, payload));
      this.currentLessonId = saved.id;
      let videoId = saved.videos[0]?.id;

      if (this.videoFile && this.uploadedVideoName !== this.videoFile.name) {
        const uploadedVideo = await firstValueFrom(this.api.uploadVideo(saved.id, this.videoFile, durationSeconds));
        videoId = uploadedVideo.id;
        this.uploadedVideoName = this.videoFile.name;
      }
      if (videoId) await firstValueFrom(this.api.updateVideo(videoId, durationSeconds, this.adminSourceUrl.trim() || null, this.adminSourceLinkLabel.trim() || null));
      if (this.coverFile) {
        await firstValueFrom(this.api.uploadThumbnail(saved.id, this.coverFile));
        this.uploadedCoverName = this.coverFile.name;
        this.coverFile = null;
      }
      if (publish) await firstValueFrom(this.api.publishLesson(saved.id));

      this.adminMessage = publish ? 'Leçon publiée et ajoutée au catalogue.' : 'Brouillon enregistré sur le serveur.';
      this.loadAdminLessons();
      if (publish) this.loadCatalog();
    } catch (error) {
      this.adminError = this.apiError(error, 'La sauvegarde a échoué.');
    } finally {
      this.adminBusy = false;
    }
  }

  editAdminLesson(lesson: LearningLessonDto): void {
    this.currentLessonId = lesson.id;
    this.adminTitle = lesson.title;
    this.adminLevel = lesson.level;
    this.adminTheme = lesson.domain;
    this.adminDescription = lesson.description;
    this.adminDuration = lesson.videos[0]?.duration_seconds === null || lesson.videos[0]?.duration_seconds === undefined ? '' : this.formatTime(lesson.videos[0].duration_seconds);
    this.adminSourceUrl = lesson.videos[0]?.source_url ?? '';
    this.adminSourceLinkLabel = lesson.videos[0]?.source_link_label ?? '';
    this.adminSegments = lesson.segments.map((segment, index) => {
      const tokens = this.tokenize(segment.text, index);
      const blanksByPosition = new Map(segment.blanks.map((blank) => [blank.position, blank]));
      let offset = 0;
      for (const token of tokens) {
        const blank = blanksByPosition.get(offset);
        if (token.kind === 'word' && blank) {
          token.selected = true;
          token.acceptedVariants = blank.accepted_variants.join(', ');
          token.acceptMutations = blank.accept_mutations;
        }
        offset += token.text.length;
      }
      return {
        id: segment.id ?? index + 1,
        start: (segment.start_ms ?? 0) / 1000,
        end: (segment.end_ms ?? segment.start_ms ?? 0) / 1000,
        tokens,
        translation: segment.translation,
      };
    });
    this.transcriptText = this.serializeAdminTranscript();
    this.transcriptFileName = 'Transcription horodatée enregistrée';
    this.adminVocabulary = lesson.vocabulary.map((item) => ({ word: item.term, translation: item.translation, example: item.note }));
    this.adminGrammar = lesson.grammar[0]
      ? { title: lesson.grammar[0].title, explanation: lesson.grammar[0].explanation, example: lesson.grammar[0].example, translation: lesson.grammar[0].translation }
      : { title: '', explanation: '', example: '', translation: '' };
    this.videoFile = null;
    this.activeMediaIsAudio = lesson.videos[0]?.content_type.startsWith('audio/') ?? false;
    this.activeCoverUrl = lesson.thumbnail_url ?? '';
    this.coverFile = null;
    this.uploadedCoverName = lesson.thumbnail_url ? 'Jaquette enregistrée' : '';
    if (lesson.thumbnail_url) {
      this.api.loadThumbnail(lesson.id).subscribe({
        next: (blob) => this.setCoverPreview(URL.createObjectURL(blob)),
        error: (error) => { this.adminError = this.apiError(error, 'Impossible de charger la jaquette existante.'); },
      });
    } else {
      this.setCoverPreview('');
    }
    this.uploadedVideoName = lesson.videos[0]?.original_filename ?? '';
    this.videoName = this.uploadedVideoName;
    if (lesson.videos[0]) {
      this.api.loadVideo(lesson.videos[0].id).subscribe({
        next: (blob) => this.setVideoUrl(URL.createObjectURL(blob), lesson.videos[0].original_filename),
        error: (error) => { this.adminError = this.apiError(error, 'Impossible de charger la vidéo existante.'); },
      });
    } else {
      this.setVideoUrl('', '');
    }
    this.adminError = '';
    this.adminMessage = `Modification de « ${lesson.title} » (${lesson.status}).`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  newAdminLesson(): void {
    this.currentLessonId = null;
    this.adminTitle = '';
    this.adminLevel = 'A2';
    this.adminTheme = '';
    this.adminDescription = '';
    this.adminDuration = '';
    this.adminSourceUrl = '';
    this.adminSourceLinkLabel = '';
    this.transcriptText = '';
    this.transcriptFileName = '';
    this.adminSegments = [];
    this.adminVocabulary = [];
    this.adminGrammar = { title: '', explanation: '', example: '', translation: '' };
    this.videoFile = null;
    this.activeMediaIsAudio = false;
    this.activeCoverUrl = '';
    this.activeSourceUrl = '';
    this.coverFile = null;
    this.uploadedCoverName = '';
    this.setCoverPreview('');
    this.uploadedVideoName = '';
    this.setVideoUrl('', '');
    this.adminError = '';
    this.adminMessage = 'Nouvelle leçon prête.';
  }

  syncExercisePageWithVideo(event: Event): void {
    const currentTime = (event.currentTarget as HTMLVideoElement).currentTime;
    this.currentVideoTime = currentTime;
    const activeSegment = this.activeLesson.segments.find((segment) => currentTime >= segment.start && currentTime <= segment.end);
    if (activeSegment && activeSegment.id !== this.lastCenteredSegmentId) {
      this.lastCenteredSegmentId = activeSegment.id;
      queueMicrotask(() => {
        this.centerActiveTranscriptSegment(activeSegment.id);
        if (this.screen === 'result' && this.resultTab === 'translation') this.centerActiveTranslationSegment(activeSegment.id);
      });
    }
    if (this.screen !== 'exercise') return;
    let matchingPage = 0;
    let previousStart = this.exercisePages[0]?.[0]?.start ?? -1;
    for (let index = 1; index < this.exercisePages.length; index++) {
      const firstSegment = this.exercisePages[index][0];
      if (!firstSegment) continue;
      if (firstSegment.start <= previousStart) continue;
      previousStart = firstSegment.start;
      if (currentTime >= firstSegment.start) matchingPage = index;
      else break;
    }
    if (matchingPage !== this.exercisePage) this.exercisePage = matchingPage;
  }

  private centerActiveTranscriptSegment(segmentId: number, smooth = true): void {
    const container = this.transcriptScroll?.nativeElement;
    const element = this.transcriptSegmentElements?.find((item) => Number(item.nativeElement.dataset['segmentId']) === segmentId)?.nativeElement;
    if (!container || !element) return;
    container.style.setProperty('--transcript-center-space', `${Math.max(0, container.clientHeight / 2 - element.offsetHeight / 2)}px`);
    const containerRect = container.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();
    const target = container.scrollTop + elementRect.top - containerRect.top - container.clientHeight / 2 + elementRect.height / 2;
    container.scrollTo({ top: Math.max(0, target), behavior: smooth ? 'smooth' : 'auto' });
  }

  private centerActiveTranslationSegment(segmentId: number, smooth = true): void {
    const container = this.translationScroll?.nativeElement;
    const element = this.translationSegmentElements?.find((item) => Number(item.nativeElement.dataset['segmentId']) === segmentId)?.nativeElement;
    if (!container || !element) return;
    container.style.setProperty('--translation-row-height', `${Math.max(86, Math.floor((container.clientHeight - 18) / 3))}px`);
    const target = element.offsetTop - container.clientHeight / 2 + element.offsetHeight / 2;
    container.scrollTo({ top: Math.max(0, target), behavior: smooth ? 'smooth' : 'auto' });
  }

  private centerActiveAdminPreviewSegment(segmentId: number, smooth = true): void {
    const container = this.adminPreviewScroll?.nativeElement;
    const element = this.adminPreviewSegmentElements?.find((item) => Number(item.nativeElement.dataset['segmentId']) === segmentId)?.nativeElement;
    if (!container || !element) return;
    const target = container.scrollTop + element.getBoundingClientRect().top - container.getBoundingClientRect().top - container.clientHeight / 2 + element.offsetHeight / 2;
    container.scrollTo({ top: Math.max(0, target), behavior: smooth ? 'smooth' : 'auto' });
  }

  selectResultTab(tab: ResultTab): void {
    this.resultTab = tab;
    if (tab !== 'translation') return;
    const active = this.activeLesson.segments.find((segment) => this.isSegmentActive(segment)) ?? this.activeLesson.segments[0];
    if (active) queueMicrotask(() => this.centerActiveTranslationSegment(active.id, false));
  }

  toggleSubtitles(language: 'br' | 'fr'): void {
    this.subtitleLanguage = this.subtitleLanguage === language ? 'off' : language;
  }

  async selectTranscript(event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.transcriptFileName = file.name;
    this.transcriptText = await file.text();
    this.parseTranscript();
  }

  scheduleTranscriptParsing(): void {
    if (this.transcriptParsingTimer) window.clearTimeout(this.transcriptParsingTimer);
    this.transcriptParsingTimer = window.setTimeout(() => {
      this.transcriptParsingTimer = undefined;
      this.parseTranscript();
    }, 500);
  }

  parseTranscript(): void {
    this.adminError = ''; this.adminMessage = '';
    const source = this.transcriptText.trim();
    if (!source) { this.adminSegments = []; this.adminError = 'Ajoute ou colle une transcription avant de continuer.'; return; }
    const timed = source.includes('-->');
    const parsed = timed ? this.parseTimedTranscript(source) : this.parsePlainText(source);
    if (!parsed.length) { this.adminSegments = []; this.adminError = 'Aucun segment exploitable n’a été trouvé.'; return; }
    const previousSegments = [...this.adminSegments];
    const claimedPrevious = new Set<AdminSegment>();
    let nextSegmentId = Math.max(0, ...previousSegments.map((segment) => segment.id)) + 1;
    this.adminSegments = parsed.map((segment, index) => {
      const previous = this.matchPreviousAdminSegment(segment, index, previousSegments, claimedPrevious);
      if (previous) claimedPrevious.add(previous);
      const tokens = this.tokenize(segment.text, index);
      if (previous && this.normalize(this.displayAdminSegmentText(previous)) === this.normalize(segment.text)) {
        const selectedWords = new Map(previous.tokens.filter((token) => token.selected).map((token) => [this.normalize(token.text), token]));
        for (const token of tokens) this.restoreTokenOptions(token, selectedWords.get(this.normalize(token.text)));
      }
      return { id: previous?.id ?? nextSegmentId++, start: segment.start, end: segment.end, tokens, translation: previous?.translation ?? '' };
    });
    this.adminMessage = `${this.adminSegments.length} segment(s) prêt(s). Clique sur les mots à masquer.`;
  }

  private matchPreviousAdminSegment(
    segment: { start: number; end: number; text: string },
    index: number,
    previousSegments: AdminSegment[],
    claimed: Set<AdminSegment>,
  ): AdminSegment | undefined {
    const available = previousSegments.filter((item) => !claimed.has(item));
    const sameTiming = available.find((item) => Math.abs(item.start - segment.start) <= .15 && Math.abs(item.end - segment.end) <= .15);
    if (sameTiming) return sameTiming;
    const normalizedText = this.normalize(segment.text);
    const sameText = available.find((item) => this.normalize(this.displayAdminSegmentText(item)) === normalizedText);
    if (sameText) return sameText;
    const closeTiming = available
      .map((item) => ({ item, distance: Math.abs(item.start - segment.start) + Math.abs(item.end - segment.end) }))
      .filter((candidate) => candidate.distance <= 2)
      .sort((left, right) => left.distance - right.distance)[0]?.item;
    if (closeTiming) return closeTiming;
    const samePosition = previousSegments[index];
    return samePosition && !claimed.has(samePosition) ? samePosition : undefined;
  }

  toggleToken(token: AdminToken): void {
    if (token.kind !== 'word') return;
    token.selected = !token.selected;
  }

  addVocabularyItem(): void { this.adminVocabulary.push({ word: '', translation: '', example: '' }); }
  removeVocabularyItem(index: number): void { this.adminVocabulary.splice(index, 1); }

  previewAdminLesson(): void {
    this.adminError = '';
    if (!this.adminSegments.length) { this.adminError = 'Analyse d’abord une transcription.'; return; }
    if (!this.selectedAdminTokens.length) { this.adminError = 'Sélectionne au moins un mot à masquer.'; return; }
    this.activeLesson = this.lessonFromAdmin();
    this.resetAnswers(); this.mode = 'learn'; this.screen = 'intro';
    window.history.pushState({}, '', '/');
    this.schedulePlayerHeightSync();
  }

  exportLesson(): void {
    this.adminError = '';
    if (!this.adminSegments.length || !this.selectedAdminTokens.length) { this.adminError = 'Il faut une transcription et au moins un trou avant l’export.'; return; }
    const lesson = this.lessonFromAdmin();
    const payload = { version: 1, video: this.videoName || null, ...lesson, segments: lesson.segments.map((segment) => ({ id: segment.id, start: segment.start, end: segment.end, translation: segment.translation, parts: segment.parts.map((part) => part.blank ? { blank: { answer: part.blank.answer, accepted: part.blank.accepted } } : { text: part.text }) })) };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${this.slugify(this.adminTitle || 'lecon')}.json`; anchor.click();
    URL.revokeObjectURL(url); this.adminMessage = 'Le fichier JSON a été exporté.';
  }

  previousExercisePage(): void { if (this.exercisePage > 0) this.exercisePage--; }
  nextExercisePage(): void { if (this.exercisePage < this.exercisePageCount - 1) this.exercisePage++; }
  validate(): void { this.exercisePage = 0; this.screen = 'correction'; }
  showResult(): void {
    this.historicalProgress = null;
    this.stopReplay(); this.subtitleLanguage = 'off'; this.resultTab = 'result'; this.screen = 'result';
    this.recordProgress('completed', this.score);
    this.schedulePlayerHeightSync();
  }
  retry(): void { this.stopReplay(); this.resetAnswers(); this.exercisePage = 0; this.screen = 'exercise'; }
  isCorrect(blank: Blank): boolean {
    const value = this.normalizeAnswer(blank.value);
    const accepted = blank.accepted.flatMap((answer) => blank.acceptMutations ? this.bretonMutationForms(answer) : [answer]);
    return accepted.some((answer) => this.normalizeAnswer(answer) === value);
  }

  replay(blank: Blank): void {
    const video = this.lessonVideo?.nativeElement;
    if (!video || !this.videoUrl) return;
    this.stopReplay(); this.replayingId = blank.id;
    video.currentTime = Math.min(blank.start, Number.isFinite(video.duration) ? Math.max(0, video.duration - .1) : blank.start);
    void video.play();
    this.replayTimer = window.setInterval(() => { if (video.currentTime >= blank.end || video.ended) this.stopReplay(); }, 120);
  }

  formatTime(seconds: number): string { return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`; }
  displaySegmentText(segment: LessonSegment): string { return this.segmentText(segment); }
  displayAdminSegmentText(segment: AdminSegment): string { return segment.tokens.map((token) => token.text).join(''); }
  segmentIdFor(token: AdminToken): number { return this.adminSegments.find((segment) => segment.tokens.includes(token))?.id ?? 0; }
  ngOnDestroy(): void {
    this.stopReplay();
    this.panelResizeObserver?.disconnect();
    if (this.transcriptParsingTimer) window.clearTimeout(this.transcriptParsingTimer);
    if (this.videoUrl) URL.revokeObjectURL(this.videoUrl);
    if (this.coverPreviewUrl) URL.revokeObjectURL(this.coverPreviewUrl);
  }

  private lessonFromAdmin(): Lesson {
    return {
      title: this.adminTitle.trim() || 'Leçon sans titre', level: this.adminLevel, duration: this.videoName ? 'Vidéo locale' : 'Durée inconnue',
      theme: this.adminTheme.trim() || 'Non classé', description: this.adminDescription.trim(),
      segments: this.adminSegments.map((segment) => ({ id: segment.id, start: segment.start, end: segment.end, translation: segment.translation.trim(), parts: segment.tokens.map((token) => token.selected ? { blank: this.blank(`segment-${segment.id}-${token.id}`, token.text, [], segment.start, segment.end) } : { text: token.text }) })),
      vocabulary: this.adminVocabulary.filter((item) => item.word.trim() && item.translation.trim()).map((item) => ({ word: item.word.trim(), translation: item.translation.trim(), example: item.example.trim() })),
      grammar: this.adminGrammar.title.trim() ? [{ title: this.adminGrammar.title.trim(), explanation: this.adminGrammar.explanation.trim(), example: this.adminGrammar.example.trim(), translation: this.adminGrammar.translation.trim() }] : [],
    };
  }

  private beginLesson(): boolean {
    if (!this.blanks.length) return false;
    this.resetAnswers();
    this.exercisePage = 0;
    this.lastCenteredSegmentId = null;
    this.screen = 'exercise';
    this.recordProgress('started', 0);
    const initialSegment = this.activeLesson.segments.find((segment) => this.currentVideoTime >= segment.start && this.currentVideoTime <= segment.end) ?? this.activeLesson.segments[0];
    if (initialSegment) {
      this.lastCenteredSegmentId = initialSegment.id;
      queueMicrotask(() => this.centerActiveTranscriptSegment(initialSegment.id, false));
    }
    this.schedulePlayerHeightSync();
    return true;
  }

  private adminLessonPayload(): LearningLessonWrite {
    return {
      title: this.adminTitle.trim() || 'Leçon sans titre',
      level: this.adminLevel,
      domain: this.adminTheme.trim() || 'Non classé',
      description: this.adminDescription.trim(),
      segments: this.adminSegments.map((segment, segmentIndex) => {
        let offset = 0;
        const blanks = segment.tokens.flatMap((token) => {
          const position = offset;
          offset += token.text.length;
          return token.selected ? [{
            position,
            answer: token.text,
            accepted_variants: this.parseAcceptedVariants(token.acceptedVariants),
            accept_mutations: token.acceptMutations,
          }] : [];
        });
        return {
          position: segmentIndex,
          start_ms: Math.round(segment.start * 1000),
          end_ms: Math.round(segment.end * 1000),
          text: this.displayAdminSegmentText(segment),
          translation: segment.translation.trim(),
          blanks,
        };
      }),
      vocabulary: this.adminVocabulary
        .filter((item) => item.word.trim() && item.translation.trim())
        .map((item, position) => ({ position, term: item.word.trim(), translation: item.translation.trim(), note: item.example.trim() })),
      grammar: this.adminGrammar.title.trim() && this.adminGrammar.explanation.trim() ? [{
        position: 0,
        title: this.adminGrammar.title.trim(),
        explanation: this.adminGrammar.explanation.trim(),
        example: this.adminGrammar.example.trim(),
        translation: this.adminGrammar.translation.trim(),
      }] : [],
    };
  }

  private lessonFromApi(source: LearningLessonDto): Lesson {
    const duration = source.videos[0]?.duration_seconds;
    return {
      title: source.title,
      level: source.level,
      theme: source.domain,
      description: source.description,
      duration: duration === null || duration === undefined ? 'Durée inconnue' : this.formatTime(duration),
      segments: source.segments.map((segment) => {
        const parts: PlayerPart[] = [];
        let offset = 0;
        for (const blank of [...segment.blanks].sort((a, b) => a.position - b.position)) {
          if (blank.position > offset) parts.push({ text: segment.text.slice(offset, blank.position) });
          parts.push({ blank: this.blank(`api-${segment.id}-${blank.id}`, blank.answer, blank.accepted_variants, (segment.start_ms ?? 0) / 1000, (segment.end_ms ?? 0) / 1000, blank.accept_mutations) });
          offset = blank.position + blank.answer.length;
        }
        if (offset < segment.text.length) parts.push({ text: segment.text.slice(offset) });
        return {
          id: segment.id ?? segment.position,
          start: (segment.start_ms ?? 0) / 1000,
          end: (segment.end_ms ?? segment.start_ms ?? 0) / 1000,
          translation: segment.translation,
          parts,
        };
      }),
      vocabulary: source.vocabulary.map((item) => ({ word: item.term, translation: item.translation, example: item.note })),
      grammar: source.grammar.map((item) => ({ title: item.title, explanation: item.explanation, example: item.example, translation: item.translation })),
    };
  }

  private loadCatalog(): void {
    this.api.listPublishedLessons().subscribe({
      next: (lessons) => {
        this.backendAvailable = true;
        this.catalogLessons = lessons.map((lesson, index) => ({
          id: lesson.id,
          title: lesson.title,
          level: lesson.level,
          theme: lesson.domain,
          duration: lesson.videos[0]?.duration_seconds === null || lesson.videos[0]?.duration_seconds === undefined
            ? 'Durée inconnue'
            : this.formatTime(lesson.videos[0].duration_seconds),
          durationSeconds: lesson.videos[0]?.duration_seconds ?? null,
          questions: lesson.segments.reduce((total, segment) => total + segment.blanks.length, 0),
          status: 'Nouveau',
          progress: this.progressPercent(lesson.id),
          visual: ['coast', 'town', 'music', 'market', 'country', 'weather', 'history', 'harbor'][index % 8],
          thumbnail: lesson.thumbnail_url ?? (lesson.id === 1 ? '/assets/lesson-1-thumbnail.webp' : undefined),
          source: lesson,
        }));
      },
      error: () => {
        this.backendAvailable = false;
        this.catalogLessons = [...this.demoCatalogLessons];
      },
    });
  }

  private loadLocalProgress(): void {
    try {
      this.progressRecords = JSON.parse(localStorage.getItem('keltiaLearn.progress') || '[]') as StoredProgress[];
    } catch {
      this.progressRecords = [];
    }
  }

  loadProgress(): void {
    if (!this.api.user()) { this.loadLocalProgress(); this.applyProgressToCatalog(); return; }
    this.api.listProgress().subscribe({
      next: (records) => {
        this.progressRecords = records.map((item) => this.progressFromApi(item));
        this.applyProgressToCatalog();
      },
      error: () => { this.loadLocalProgress(); this.applyProgressToCatalog(); },
    });
  }

  private recordProgress(status: 'started' | 'completed', score: number): void {
    const lessonId = this.activeCatalogLesson?.id;
    if (!lessonId) return;
    const existing = this.progressRecords.find((item) => item.lessonId === lessonId);
    const record: StoredProgress = {
      lessonId,
      status: status === 'completed' || existing?.status === 'completed' ? 'completed' : 'started',
      bestScore: Math.max(existing?.bestScore ?? 0, score),
      totalQuestions: Math.max(existing?.totalQuestions ?? 0, this.blanks.length),
      attempts: (existing?.attempts ?? 0) + (status === 'completed' ? 1 : 0),
      updatedAt: new Date().toISOString(),
    };
    this.progressRecords = [...this.progressRecords.filter((item) => item.lessonId !== lessonId), record];
    localStorage.setItem('keltiaLearn.progress', JSON.stringify(this.progressRecords));
    this.applyProgressToCatalog();
    if (this.api.user()) this.api.saveProgress(lessonId, status, score, this.blanks.length).subscribe();
  }

  private async syncLocalProgressToServer(): Promise<void> {
    const serverRecords = await firstValueFrom(this.api.listProgress());
    for (const record of this.progressRecords) {
      const serverRecord = serverRecords.find((item) => item.lesson_id === record.lessonId);
      if (serverRecord && new Date(serverRecord.updated_at) >= new Date(record.updatedAt)) continue;
      await firstValueFrom(this.api.saveProgress(record.lessonId, record.status, record.bestScore, record.totalQuestions));
    }
  }

  private progressFromApi(item: LearningProgressDto): StoredProgress {
    return { lessonId: item.lesson_id, status: item.status, bestScore: item.best_score, totalQuestions: item.total_questions, attempts: item.attempts, updatedAt: item.updated_at };
  }

  private progressPercent(lessonId: number): number {
    const record = this.progressRecords.find((item) => item.lessonId === lessonId);
    return record?.status === 'completed' ? 100 : record ? 25 : 0;
  }

  private applyProgressToCatalog(): void {
    this.catalogLessons = this.catalogLessons.map((lesson) => {
      const record = lesson.id ? this.progressRecords.find((item) => item.lessonId === lesson.id) : undefined;
      return {
        ...lesson,
        progress: lesson.id ? this.progressPercent(lesson.id) : lesson.progress,
        status: lesson.id ? (record?.status === 'completed' ? 'Terminé ✓' : record ? 'En cours' : 'Nouveau') : lesson.status,
      };
    });
  }

  private loadAdminLessons(): void {
    this.api.listAdminLessons().subscribe({
      next: (lessons) => {
        this.backendAvailable = true;
        this.adminLessons = lessons;
      },
      error: (error) => {
        this.adminError = this.apiError(error, 'Impossible de charger les leçons existantes.');
      },
    });
  }

  private setVideoUrl(url: string, name: string): void {
    if (this.videoUrl.startsWith('blob:')) URL.revokeObjectURL(this.videoUrl);
    this.videoUrl = url;
    this.videoName = name;
    queueMicrotask(() => this.lessonVideo?.nativeElement.load());
  }

  private setCoverPreview(url: string): void {
    if (this.coverPreviewUrl.startsWith('blob:')) URL.revokeObjectURL(this.coverPreviewUrl);
    this.coverPreviewUrl = url;
    if (this.activeMediaIsAudio) this.activeCoverUrl = url;
  }

  private apiError(error: unknown, fallback: string): string {
    if (typeof error === 'object' && error !== null) {
      const response = error as { status?: number; error?: { detail?: string | Array<{ msg?: string }> } };
      if (response.status === 0) {
        this.backendAvailable = false;
        return 'Backend inaccessible. Lance ./start_learning.sh depuis la racine du dépôt.';
      }
      const detail = response.error?.detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' · ') || fallback;
    }
    return fallback;
  }

  private parseTimedTranscript(source: string): Array<{ start: number; end: number; text: string }> {
    const blocks = source.replace(/^WEBVTT[^\n]*\n+/i, '').replace(/\r/g, '').trim().split(/\n{2,}/);
    const output: Array<{ start: number; end: number; text: string }> = [];
    for (const block of blocks) {
      const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
      const timingIndex = lines.findIndex((line) => line.includes('-->'));
      if (timingIndex < 0) continue;
      const [startRaw, endWithSettings] = lines[timingIndex].split('-->').map((value) => value.trim());
      const start = this.timestampToSeconds(startRaw); const end = this.timestampToSeconds(endWithSettings.split(/\s+/)[0]);
      const text = lines.slice(timingIndex + 1).join('\n').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').replace(/\[br\]/gi, '\n').trim();
      if (text && Number.isFinite(start) && Number.isFinite(end)) output.push({ start, end, text });
    }
    return output;
  }

  private parsePlainText(source: string): Array<{ start: number; end: number; text: string }> {
    const lines = source.split(/\n+/).map((line) => line.trim().replace(/\[br\]/gi, '\n')).filter(Boolean);
    const units = lines.length > 1 ? lines : source.split(/(?<=[.!?])\s+/).map((line) => line.trim()).filter(Boolean);
    return units.map((text, index) => ({ start: index * 8, end: index * 8 + 8, text }));
  }

  private tokenize(text: string, segmentIndex: number): AdminToken[] {
    const pieces = text.match(/[\p{L}\p{N}][\p{L}\p{N}’'’-]*|\s+|[^\p{L}\p{N}\s]+/gu) ?? [text];
    return pieces.map((piece, index) => ({ id: `${segmentIndex}-${index}`, text: piece, kind: /^\s+$/u.test(piece) ? 'space' : /^[\p{L}\p{N}]/u.test(piece) ? 'word' : 'punctuation', selected: false, acceptedVariants: '', acceptMutations: false }));
  }

  private timestampToSeconds(value: string): number {
    const parts = value.replace(',', '.').split(':').map(Number);
    if (parts.some((part) => !Number.isFinite(part))) return Number.NaN;
    return parts.length === 3 ? parts[0] * 3600 + parts[1] * 60 + parts[2] : parts.length === 2 ? parts[0] * 60 + parts[1] : Number.NaN;
  }

  private manualDurationSeconds(): number | null {
    const value = this.adminDuration.trim();
    if (!value) return this.videoDurationSeconds;
    if (/^\d+$/.test(value)) return Number(value);
    const parts = value.split(':').map(Number);
    if (parts.length === 2 && parts.every((part) => Number.isFinite(part)) && parts[1] >= 0 && parts[1] < 60) {
      return Math.round(parts[0] * 60 + parts[1]);
    }
    if (parts.length === 3 && parts.every((part) => Number.isFinite(part)) && parts[1] >= 0 && parts[1] < 60 && parts[2] >= 0 && parts[2] < 60) {
      return Math.round(parts[0] * 3600 + parts[1] * 60 + parts[2]);
    }
    return null;
  }

  private serializeAdminTranscript(): string {
    return this.adminSegments.map((segment, index) => [
      String(index + 1),
      `${this.formatSrtTimestamp(segment.start)} --> ${this.formatSrtTimestamp(segment.end)}`,
      this.displayAdminSegmentText(segment),
    ].join('\n')).join('\n\n');
  }

  private formatSrtTimestamp(seconds: number): string {
    const safeSeconds = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
    const milliseconds = Math.round(safeSeconds * 1000);
    const hours = Math.floor(milliseconds / 3_600_000);
    const minutes = Math.floor(milliseconds % 3_600_000 / 60_000);
    const secs = Math.floor(milliseconds % 60_000 / 1000);
    const millis = milliseconds % 1000;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(millis).padStart(3, '0')}`;
  }

  private endsSentence(segment: LessonSegment): boolean {
    return /[.!?…][»”"')\]]*$/u.test(this.segmentText(segment).trim());
  }

  private splitLongSegment(segment: LessonSegment): LessonSegment[] {
    if (this.segmentText(segment).length <= this.maxPageTextWeight) return [segment];

    const fragments: LessonSegment[] = [];
    let parts: PlayerPart[] = [];
    let weight = 0;
    const flush = (): void => {
      if (!parts.length) return;
      fragments.push({ ...segment, parts });
      parts = [];
      weight = 0;
    };
    const appendText = (text: string): void => {
      const pieces = text.match(/\S+\s*|\s+/gu) ?? [text];
      for (const piece of pieces) {
        if (weight > 0 && weight + piece.length > this.maxPageTextWeight) flush();
        parts.push({ text: piece });
        weight += piece.length;
      }
    };

    for (const part of segment.parts) {
      if (part.blank) {
        const blankWeight = Math.max(part.blank.answer.length, 12);
        if (weight > 0 && weight + blankWeight > this.maxPageTextWeight) flush();
        parts.push(part);
        weight += blankWeight;
      } else if (part.text) {
        appendText(part.text);
      }
    }
    flush();
    return fragments.length ? fragments : [segment];
  }

  private segmentText(segment: LessonSegment): string {
    return segment.parts.map((part) => part.text ?? part.blank?.answer ?? '').join('');
  }

  private blank(id: string, answer: string, variants: string[], start: number, end: number, acceptMutations = false): Blank { return { id, answer, accepted: [answer, ...variants], acceptMutations, start, end, value: '' }; }
  private schedulePlayerHeightSync(): void {
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => this.syncPlayerHeight()));
  }
  private resetAnswers(): void { for (const blank of this.blanks) blank.value = ''; }
  private normalize(value: string): string { return value.trim().toLocaleLowerCase('br').replace(/[’']/g, "'").replace(/\s+/g, ' '); }
  private normalizeAnswer(value: string): string { return this.normalize(value).replace(/\s*'\s*/g, "'").replace(/\s+/g, ''); }
  private parseAcceptedVariants(value: string): string[] { return [...new Set(value.split(/[,;\n]/).map((item) => item.trim()).filter(Boolean))]; }
  private restoreTokenOptions(token: AdminToken, previous?: AdminToken): void {
    if (token.kind !== 'word' || !previous) return;
    token.selected = true;
    token.acceptedVariants = previous.acceptedVariants;
    token.acceptMutations = previous.acceptMutations;
  }
  private bretonMutationForms(value: string): string[] {
    const normalized = this.normalize(value);
    const groups = [
      ['gw', 'w'], ['c’h', "c'h", 'g', 'k'], ['b', 'v', 'p', 'm'],
      ['d', 'z', 't', 'n'], ['p', 'b', 'f'], ['t', 'd', 'z'], ['k', 'g', 'c’h', "c'h"],
    ];
    for (const group of groups) {
      const prefix = group.find((candidate) => normalized.startsWith(this.normalize(candidate)));
      if (!prefix) continue;
      const suffix = normalized.slice(this.normalize(prefix).length);
      return [...new Set([value, ...group.map((candidate) => candidate + suffix)])];
    }
    return [value];
  }
  private slugify(value: string): string { return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'lecon'; }
  private stopReplay(): void { if (this.replayTimer) window.clearInterval(this.replayTimer); this.replayTimer = undefined; this.replayingId = ''; this.lessonVideo?.nativeElement.pause(); }
}
