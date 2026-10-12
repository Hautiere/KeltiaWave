export interface DomainOption {
  value: string;
  label: string;
  labelKey: string;
  icon?: string;
  tone?: string;
}

export const DOMAIN_OPTIONS: DomainOption[] = [
  { value: '', label: 'Non défini', labelKey: 'domain.undefined' },
  { value: 'rencontres', label: 'Se présenter et se rencontrer', labelKey: 'domain.introductions', icon: '◉', tone: 'green' },
  { value: 'maison-quotidien', label: 'Maison et vie quotidienne', labelKey: 'domain.dailyLife', icon: '⌂', tone: 'green' },
  { value: 'famille-relations', label: 'Famille et relations', labelKey: 'domain.family', icon: '●●', tone: 'orange' },
  { value: 'alimentation-achats', label: 'Manger, cuisiner et acheter', labelKey: 'domain.foodShopping', icon: '◌', tone: 'rose' },
  { value: 'deplacements', label: 'Se déplacer', labelKey: 'domain.transport', icon: '▣', tone: 'sky' },
  { value: 'travail-etudes', label: 'Travail et études', labelKey: 'domain.workStudies', icon: '▤', tone: 'brown' },
  { value: 'sante-bien-etre', label: 'Santé et bien-être', labelKey: 'domain.health', icon: '♧', tone: 'red' },
  { value: 'nature-meteo', label: 'Nature et météo', labelKey: 'domain.nature', icon: '◒', tone: 'leaf' },
  { value: 'loisirs-sport', label: 'Loisirs et sport', labelKey: 'domain.sports', icon: '◎', tone: 'lime' },
  { value: 'culture-fetes', label: 'Culture et fêtes', labelKey: 'domain.cultureFestivals', icon: '◇', tone: 'gold' },
  { value: 'histoire-patrimoine', label: 'Histoire et patrimoine', labelKey: 'domain.historyHeritage', icon: '▥', tone: 'amber' },
  { value: 'demarches-services', label: 'Démarches et services', labelKey: 'domain.services', icon: '⌂', tone: 'slate' },
  { value: 'numerique-technologies', label: 'Numérique et technologies', labelKey: 'domain.digital', icon: '⌘', tone: 'indigo' },
];

const LEGACY_THEMES: Record<string, string> = {
  'vie-quotidienne': 'maison-quotidien', quotidien: 'maison-quotidien', daily: 'maison-quotidien', 'daily-life': 'maison-quotidien',
  famille: 'famille-relations', cuisine: 'alimentation-achats', transports: 'deplacements', transport: 'deplacements',
  travail: 'travail-etudes', education: 'travail-etudes', ecole: 'travail-etudes', 'ecole-formation': 'travail-etudes', 'ecole-et-formation': 'travail-etudes',
  sante: 'sante-bien-etre', nature: 'nature-meteo', 'nature-environnement': 'nature-meteo', 'nature-et-environnement': 'nature-meteo',
  'sports-loisirs': 'loisirs-sport', sports: 'loisirs-sport', sport: 'loisirs-sport',
  culture: 'histoire-patrimoine', patrimoine: 'histoire-patrimoine', 'culture-patrimoine': 'histoire-patrimoine',
  histoire: 'histoire-patrimoine', 'traditions-fetes': 'culture-fetes', administration: 'demarches-services',
  technologies: 'numerique-technologies', technologie: 'numerique-technologies', 'technologie-medias': 'numerique-technologies',
};

export function canonicalDomain(value?: string | null): string {
  const normalized = (value ?? '').trim().toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/&/g, 'et')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return LEGACY_THEMES[normalized] || normalized;
}

export function domainLabelKey(value?: string | null): string {
  return DOMAIN_OPTIONS.find((domain) => domain.value === canonicalDomain(value))?.labelKey || 'domain.undefined';
}
