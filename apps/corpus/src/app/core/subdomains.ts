/** Editorial taxonomy shared by Library, Komz and future learning views. */
export interface SubdomainOption {
  value: string;
  label: string;
}

const labels: Record<string, string[]> = {
  rencontres: ['Saluer & prendre congé', 'Se présenter', 'Origine & lieu de vie', 'Parler de soi', 'Goûts & préférences', 'Poser des questions'],
  'maison-quotidien': ['Maison', 'Pièces & mobilier', 'Tâches quotidiennes', 'Matin & soir', 'Objets du quotidien', 'Voisinage'],
  'famille-relations': ['Famille', 'Couple & proches', 'Amis', 'Enfants & générations', 'Relations humaines', 'Émotions & sentiments'],
  'alimentation-achats': ['Aliments & boissons', 'Repas', 'Cuisine & recettes', 'Café & restaurant', 'Marché & commerces', 'Acheter & payer'],
  deplacements: ['Se déplacer', 'Train & gare', 'Voiture & route', 'Bus & transports publics', 'Hébergement', 'Demander son chemin'],
  'nature-meteo': ['Mer & littoral', 'Campagne & paysages', 'Animaux', 'Plantes & jardin', 'Météo & saisons', 'Environnement'],
  'travail-etudes': ['Métiers', 'Lieu de travail', 'École & études', 'Apprendre', 'Réunions & échanges', 'Projets & activités'],
  'sante-bien-etre': ['Corps humain', 'Santé & symptômes', 'Médecin & pharmacie', 'Forme & fatigue', 'Sommeil & repos', 'Bien-être'],
  'culture-fetes': ['Heure & rendez-vous', 'Téléphone & messages', 'Services', 'Problèmes & imprévus', "Demander de l'aide", 'Politesse & interactions', 'Traditions & fêtes'],
  'loisirs-sport': ['Sports', 'Marche & randonnée', 'Mer & activités nautiques', 'Musique', 'Lecture & médias', 'Sorties & vacances'],
  'histoire-patrimoine': ['Histoire & patrimoine', 'Traditions & fêtes', 'Musique & danse', 'Langue bretonne', 'Arts & littérature', 'Société & vie locale'],
  'demarches-services': ['Lieux & directions', 'Signalisation', 'Horaires & dates', 'Prix & paiement', 'Administration', 'Urgences & services'],
  'numerique-technologies': ['Internet', 'Téléphone & applications', 'Ordinateur', 'Messages & réseaux', 'Services numériques', 'Sécurité en ligne'],
};

const englishLabels: Record<string, string[]> = {
  rencontres: ['Greetings & farewells', 'Introducing yourself', 'Where you are from & where you live', 'Talking about yourself', 'Likes & preferences', 'Asking questions'],
  'maison-quotidien': ['Home', 'Rooms & furniture', 'Daily tasks', 'Morning & evening', 'Everyday objects', 'Neighbours'],
  'famille-relations': ['Family', 'Partners & loved ones', 'Friends', 'Children & generations', 'Human relationships', 'Emotions & feelings'],
  'alimentation-achats': ['Food & drinks', 'Meals', 'Cooking & recipes', 'Cafés & restaurants', 'Markets & shops', 'Buying & paying'],
  deplacements: ['Getting around', 'Trains & stations', 'Cars & roads', 'Buses & public transport', 'Accommodation', 'Asking for directions'],
  'nature-meteo': ['Sea & coast', 'Countryside & landscapes', 'Animals', 'Plants & gardens', 'Weather & seasons', 'Environment'],
  'travail-etudes': ['Jobs', 'Workplace', 'School & studies', 'Learning', 'Meetings & conversations', 'Projects & activities'],
  'sante-bien-etre': ['Human body', 'Health & symptoms', 'Doctors & pharmacies', 'Fitness & tiredness', 'Sleep & rest', 'Wellbeing'],
  'culture-fetes': ['Time & appointments', 'Phone & messages', 'Services', 'Problems & surprises', 'Asking for help', 'Politeness & interactions', 'Traditions & celebrations'],
  'loisirs-sport': ['Sports', 'Walking & hiking', 'Sea & water activities', 'Music', 'Reading & media', 'Outings & holidays'],
  'histoire-patrimoine': ['History & heritage', 'Traditions & celebrations', 'Music & dance', 'Breton language', 'Arts & literature', 'Society & local life'],
  'demarches-services': ['Places & directions', 'Signs', 'Times & dates', 'Prices & payment', 'Administration', 'Emergencies & services'],
  'numerique-technologies': ['Internet', 'Phones & apps', 'Computers', 'Messages & social media', 'Digital services', 'Online safety'],
};

const welshLabels: Record<string, string[]> = {
  rencontres: ['Cyfarchion a ffarwelio', 'Cyflwyno eich hun', 'O ble rydych chi a ble rydych chi’n byw', 'Siarad amdanoch eich hun', 'Hoff bethau a dewisiadau', 'Gofyn cwestiynau'],
  'maison-quotidien': ['Cartref', 'Ystafelloedd a dodrefn', 'Tasgau dyddiol', 'Bore a nos', 'Gwrthrychau bob dydd', 'Cymdogion'],
  'famille-relations': ['Teulu', 'Partneriaid ac anwyliaid', 'Ffrindiau', 'Plant a chenedlaethau', 'Perthnasoedd dynol', 'Emosiynau a theimladau'],
  'alimentation-achats': ['Bwyd a diodydd', 'Prydau bwyd', 'Coginio a ryseitiau', 'Caffis a bwytai', 'Marchnadoedd a siopau', 'Prynu a thalu'],
  deplacements: ['Teithio o gwmpas', 'Trenau a gorsafoedd', 'Ceir a ffyrdd', 'Bysiau a thrafnidiaeth gyhoeddus', 'Llety', 'Gofyn am gyfarwyddiadau'],
  'nature-meteo': ['Môr ac arfordir', 'Cefn gwlad a thirweddau', 'Anifeiliaid', 'Planhigion a gerddi', 'Tywydd a thymhorau', 'Yr amgylchedd'],
  'travail-etudes': ['Swyddi', 'Man gwaith', 'Ysgol ac astudiaethau', 'Dysgu', 'Cyfarfodydd a sgyrsiau', 'Prosiectau a gweithgareddau'],
  'sante-bien-etre': ['Y corff dynol', 'Iechyd a symptomau', 'Meddygon a fferyllfeydd', 'Ffitrwydd a blinder', 'Cwsg a gorffwys', 'Lles'],
  'culture-fetes': ['Amser ac apwyntiadau', 'Ffôn a negeseuon', 'Gwasanaethau', 'Problemau a digwyddiadau annisgwyl', 'Gofyn am help', 'Cwrteisi a rhyngweithio', 'Traddodiadau a dathliadau'],
  'loisirs-sport': ['Chwaraeon', 'Cerdded a heicio', 'Môr a gweithgareddau dŵr', 'Cerddoriaeth', 'Darllen a’r cyfryngau', 'Gwibdeithiau a gwyliau'],
  'histoire-patrimoine': ['Hanes a threftadaeth', 'Traddodiadau a dathliadau', 'Cerddoriaeth a dawns', 'Iaith Lydaweg', 'Celfyddydau a llenyddiaeth', 'Cymdeithas a bywyd lleol'],
  'demarches-services': ['Lleoedd a chyfarwyddiadau', 'Arwyddion', 'Amseroedd a dyddiadau', 'Prisiau a thalu', 'Gweinyddu', 'Argyfyngau a gwasanaethau'],
  'numerique-technologies': ['Y rhyngrwyd', 'Ffonau ac apiau', 'Cyfrifiaduron', 'Negeseuon a chyfryngau cymdeithasol', 'Gwasanaethau digidol', 'Diogelwch ar-lein'],
};

export function subdomainsFor(domain: string, language = 'fr'): SubdomainOption[] {
  return (labels[domain] || []).map((label, index) => ({
    value: slug(label),
    label: language === 'en' ? (englishLabels[domain]?.[index] || label)
      : language === 'cy' ? (welshLabels[domain]?.[index] || label) : label,
  }));
}

export function subdomainLabel(domain: string, value?: string | null, language = 'fr'): string | null {
  if (!value) return null;
  return subdomainsFor(domain, language).find((option) => option.value === canonicalSubdomain(value))?.label || value;
}

/** Older imports stored the visible label; filters use its stable slug. */
export function canonicalSubdomain(value?: string | null): string {
  return value ? slug(value) : '';
}

function slug(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, 'et').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
