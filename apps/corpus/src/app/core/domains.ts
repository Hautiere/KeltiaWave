export interface DomainOption {
  value: string;
  label: string;
  labelKey: string;
}

export const DOMAIN_OPTIONS: DomainOption[] = [
  { value: '', label: 'Non defini', labelKey: 'domain.undefined' },
  { value: 'vie-quotidienne', label: 'Vie quotidienne', labelKey: 'domain.dailyLife' },
  { value: 'transports', label: 'Transports', labelKey: 'domain.transport' },
  { value: 'famille', label: 'Famille', labelKey: 'domain.family' },
  { value: 'ecole-formation', label: 'Ecole et formation', labelKey: 'domain.education' },
  { value: 'travail', label: 'Travail', labelKey: 'domain.work' },
  { value: 'sante', label: 'Sante', labelKey: 'domain.health' },
  { value: 'culture', label: 'Culture', labelKey: 'domain.culture' },
  { value: 'nature-environnement', label: 'Nature et environnement', labelKey: 'domain.nature' },
  { value: 'administration', label: 'Administration', labelKey: 'domain.administration' },
  { value: 'technologie-medias', label: 'Technologie et medias', labelKey: 'domain.technology' },
];

export function domainLabelKey(value?: string | null): string {
  return DOMAIN_OPTIONS.find((domain) => domain.value === value)?.labelKey || 'domain.undefined';
}
