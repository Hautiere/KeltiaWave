import type { AudioRead } from './api.service';

/** Shared by Listen and Komz: one reviewed reference per phrase, newest first. */
export function selectReferenceAudios(audios: AudioRead[]): AudioRead[] {
  const references = new Map<number, AudioRead>();
  const ordered = [...audios].sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
  for (const audio of ordered) {
    if (audio.status !== 'approved' || references.has(audio.phrase_id)) continue;
    const review = (audio.validations ?? []).find(item =>
      ['teacher', 'admin'].includes(item.validator_role || '') && ['approved', 'rejected'].includes(item.decision));
    const reviewed = review ? review.decision === 'approved' : ['teacher', 'admin'].includes(audio.validator_role || '');
    const ownerApproved = audio.phrase_source === 'common-voice'
      && (audio.validation_comment || '').startsWith('Approbation en lot demandée par le propriétaire');
    if (reviewed || ownerApproved) references.set(audio.phrase_id, audio);
  }
  return [...references.values()];
}
