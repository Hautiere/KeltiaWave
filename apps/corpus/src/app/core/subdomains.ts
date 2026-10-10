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

export function subdomainsFor(domain: string): SubdomainOption[] {
  return (labels[domain] || []).map((label) => ({ value: slug(label), label }));
}

export function subdomainLabel(domain: string, value?: string | null): string | null {
  if (!value) return null;
  return subdomainsFor(domain).find((option) => option.value === value)?.label || value;
}

function slug(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, 'et').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
