import type { Phrase } from '../../../core/api.service';
import { canonicalDomain } from '../../../core/domains';
import { canonicalSubdomain } from '../../../core/subdomains';

export interface ExplorerState {
  page: number;
  theme: string;
  subdomain: string;
  level: string;
  search: string;
  onlyWithAudio: boolean;
  translation: 'interface' | 'fr' | 'en' | 'cy' | 'none';
}
export const initialExplorerState = (): ExplorerState => ({ page: 1, theme: 'rencontres', subdomain: '', level: 'all', search: '', onlyWithAudio: true, translation: 'interface' });
export function komzInterface(search: string, saved: string | null): 'classic' | 'modern' {
  const explicit = new URLSearchParams(search).get('interface');
  return (explicit === 'classic' || explicit === 'modern' ? explicit : saved) === 'classic' ? 'classic' : 'modern';
}
export function normalizedText(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().replace(/[’ʼ]/g, "'").trim();
}
const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
function levelRank(phrase: Phrase): number {
  const index = LEVELS.indexOf((phrase.niveau || '').toUpperCase());
  return index < 0 ? LEVELS.length : index;
}
export function filterExplorerPhrases(phrases: Phrase[], referenceIds: ReadonlySet<number>, state: ExplorerState): Phrase[] {
  const search = normalizedText(state.search);
  return phrases.filter(phrase => canonicalDomain(phrase.theme) === state.theme
    && (!state.onlyWithAudio || referenceIds.has(phrase.id))
    && (state.subdomain === '' || (state.subdomain === '__unclassified__' ? !phrase.subdomain?.trim() : canonicalSubdomain(phrase.subdomain) === state.subdomain))
    && (state.level === 'all' || (state.level === 'unrated' ? !phrase.niveau?.trim() : phrase.niveau?.toUpperCase() === state.level))
    && (!search || normalizedText([phrase.texte, phrase.traduction_fr, phrase.traduction_en, phrase.traduction_cy].filter(Boolean).join(' ')).includes(search)))
    .sort((a, b) => levelRank(a) - levelRank(b));
}
