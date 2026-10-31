/** The speaker of an audio is independent of the source of its phrase. */
export function audioAttribution(audio: {
  origin?: string | null;
  contributor_name?: string | null;
  phrase_source?: string | null;
}, datasetSource?: string | null): string {
  if (audio.origin !== 'dataset') return audio.contributor_name?.trim() || 'Inconnu';
  const source = audio.phrase_source || datasetSource;
  return source === 'common-voice' ? 'Common Voice' : source || 'Source non renseignée';
}
