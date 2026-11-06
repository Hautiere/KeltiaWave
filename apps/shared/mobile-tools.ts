/** Presentation helpers shared by the independent web frontends; no Angular dependency. */
export type MobileLocale = 'fr' | 'en' | 'br' | 'cy';
export function mobileToolLinks() {
  const local = ['localhost', '127.0.0.1'].includes(location.hostname);
  // A second local preview stack can coexist with Docker on ports 14xxx.
  const offset = local && Number(location.port) >= 14000 && Number(location.port) < 15000 ? 10000 : 0;
  const domain = location.hostname.includes('.staging.') ? 'staging.keltiawave.com' : 'keltiawave.com';
  const tool = (name: string, port: number) => local ? `${location.protocol}//${location.hostname}:${port + offset}` : `https://${name}.${domain}`;
  return { record: tool('record', 4400), transcribe: tool('transcribe', 4500), live: tool('live', 4800), komz: `${tool('komz', 4200)}/lire`, account: `${tool('komz', 4200)}/compte`, portal: local ? `${location.protocol}//${location.hostname}:4100/` : `https://${domain}/` };
}
const LABELS: Record<string, Record<MobileLocale, string>> = {
  languages: {fr:'Langues',en:'Languages',br:'Yezhoù',cy:'Ieithoedd'},
  interface: {fr:'Langue de l’interface',en:'Interface language',br:'Yezh an etrefas',cy:'Iaith y rhyngwyneb'},
  audio: {fr:'Langue de l’audio',en:'Audio language',br:'Yezh an audio',cy:'Iaith y sain'},
  account: {fr:'Mon compte',en:'My account',br:'Ma c’hont',cy:'Fy nghyfrif'},
  close: {fr:'Fermer',en:'Close',br:'Serriñ',cy:'Cau'},
  help: {fr:'Aide et confidentialité',en:'Help and privacy',br:'Skoazell ha prevezded',cy:'Cymorth a phreifatrwydd'},
  save: {fr:'Sauver le texte',en:'Save text',br:'Enrollañ an destenn',cy:'Cadw’r testun'},
  email: {fr:'Envoyer par email',en:'Send by email',br:'Kas dre bostel',cy:'Anfon drwy e-bost'},
  share: {fr:'Partager',en:'Share',br:'Rannañ',cy:'Rhannu'},
  quality: {fr:'Whisper · Qualité',en:'Whisper · Quality',br:'Whisper · Kalite',cy:'Whisper · Ansawdd'},
  online: {fr:'Avec Internet',en:'Online',br:'Gant Internet',cy:'Ar-lein'},
  recordSubtitle: {fr:'Enregistrer et transcrire',en:'Record and transcribe',br:'Enrollañ ha treuzskrivañ',cy:'Recordio a thrawsgrifio'},
  transcribeSubtitle: {fr:'Audio / vidéo → texte',en:'Audio / video → text',br:'Audio / video → testenn',cy:'Sain / fideo → testun'},
  liveSubtitle: {fr:'Suivre une parole en direct',en:'Follow speech live',br:'Heuliañ ar gomz war-eeun',cy:'Dilyn lleferydd yn fyw'},
  komzSubtitle: {fr:'Écouter, parler, s’entraîner',en:'Listen, speak, practise',br:'Selaou, komz, pleustriñ',cy:'Gwrando, siarad, ymarfer'},
};
export function mobileLabel(key: string, language: string): string {
  return LABELS[key]?.[language as MobileLocale] ?? LABELS[key]?.fr ?? key;
}

const MOBILE_LIVE_TEXT: Record<string, Record<MobileLocale,string>> = {
  "Écoutez. Suivez. Comprenez.": {
    "fr": "Écoutez. Suivez. Comprenez.",
    "en": "Listen. Follow. Understand.",
    "br": "Selaouit. Heuilhit. Komprenit.",
    "cy": "Gwrandewch. Dilynwch. Deallwch."
  },
  "Les paroles du podcast apparaîtront ici, au rythme de l’écoute.": {
    "fr": "Les paroles du podcast apparaîtront ici, au rythme de l’écoute.",
    "en": "The podcast’s words will appear here as you listen.",
    "br": "Gerioù ar podkast a vo diskouezet amañ e-kerzh ar selaou.",
    "cy": "Bydd geiriau’r podlediad yn ymddangos yma wrth i chi wrando."
  },
  "Améliorer la lisibilité avec Whisper": {
    "fr": "Améliorer la lisibilité avec Whisper",
    "en": "Improve readability with Whisper",
    "br": "Gwellaat al lennadusted gant Whisper",
    "cy": "Gwella darllenadwyedd gyda Whisper"
  },
  "Transcription Whisper": {
    "fr": "Transcription Whisper",
    "en": "Whisper transcription",
    "br": "Treuzskrivadur Whisper",
    "cy": "Trawsgrifiad Whisper"
  },
  "Démarrer l’écoute": {
    "fr": "Démarrer l’écoute",
    "en": "Start listening",
    "br": "Kregiñ da selaou",
    "cy": "Dechrau gwrando"
  },
  "Arrêter l’écoute": {
    "fr": "Arrêter l’écoute",
    "en": "Stop listening",
    "br": "Paouez da selaou",
    "cy": "Stopio gwrando"
  },
  "Prêt à écouter": {
    "fr": "Prêt à écouter",
    "en": "Ready to listen",
    "br": "Prest da selaou",
    "cy": "Barod i wrando"
  },
  "Écoute terminée": {
    "fr": "Écoute terminée",
    "en": "Listening finished",
    "br": "Selaou echu",
    "cy": "Gwrando wedi gorffen"
  },
  "En écoute": {
    "fr": "En écoute",
    "en": "Listening",
    "br": "O selaou",
    "cy": "Yn gwrando"
  },
  "En pause": {
    "fr": "En pause",
    "en": "Paused",
    "br": "Ehanet",
    "cy": "Wedi seibio"
  },
  "Finalisation du texte…": {
    "fr": "Finalisation du texte…",
    "en": "Finalizing text…",
    "br": "O peurechuiñ an destenn…",
    "cy": "Yn cwblhau’r testun…"
  },
  "Choisissez la source audio…": {
    "fr": "Choisissez la source audio…",
    "en": "Choose the audio source…",
    "br": "Dibabit ar vammenn audio…",
    "cy": "Dewiswch y ffynhonnell sain…"
  },
  "Traitement Whisper…": {
    "fr": "Traitement Whisper…",
    "en": "Processing Whisper…",
    "br": "O tretiñ Whisper…",
    "cy": "Wrthi’n prosesu Whisper…"
  },
  "Revenir au direct ↓": {
    "fr": "Revenir au direct ↓",
    "en": "Back to live ↓",
    "br": "Distreiñ d’ar war-eeun ↓",
    "cy": "Yn ôl i’r byw ↓"
  },
  "Reprendre": {
    "fr": "Reprendre",
    "en": "Resume",
    "br": "Adkregiñ",
    "cy": "Ailddechrau"
  },
  "Pause": {
    "fr": "Pause",
    "en": "Pause",
    "br": "Ehan",
    "cy": "Saib"
  },
  "Transcription en direct": {
    "fr": "Transcription en direct",
    "en": "Live transcription",
    "br": "Treuzskrivadur war-eeun",
    "cy": "Trawsgrifiad byw"
  },
  "Partage audio du navigateur · Internet requis": {
    "fr": "Partage audio du navigateur · Internet requis",
    "en": "Browser audio sharing · Internet required",
    "br": "Rannañ audio ar merdeer · Internet ret",
    "cy": "Rhannu sain y porwr · Angen Rhyngrwyd"
  }
};
export function mobileLiveText(source: string, language: string): string { return MOBILE_LIVE_TEXT[source]?.[language as MobileLocale] ?? source; }
