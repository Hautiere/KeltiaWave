//frontend/src/app/core/models.ts
export type AudioStatus = 'pending' | 'approved' | 'rejected';

export interface AudioValidationRead {
  id: number;
  audio_id: number;
  decision: 'approved' | 'rejected' | string;
  validator?: string | null;
  validator_role?: string | null;
  validation_weight?: string | null;
  pronunciation_level?: string | null;
  pronunciation_region?: string | null;
  comment?: string | null;
  created_at: string;
}

export interface AudioRead {
  id: number;
  phrase_id: number;
  filename: string;        // ex: "data/audios/xxx.webm"
  status: AudioStatus;
  phrase_source?: string | null;
  domain?: string | null;
  speaker_region?: string | null;
  speaker_city?: string | null;
  speaker_accent?: string | null;
  speaker_level?: string | null;
  created_at: string;
  validated_at?: string | null;
  validated_by?: string | null;
  validator_role?: string | null;
  validation_weight?: string | null;
  validation_comment?: string | null;
  contributor_name?: string | null;
  contributor_email?: string | null;
  contributor_school?: string | null;
  contributor_school_level?: string | null;
  validations?: AudioValidationRead[];
}

// --- Phrases ---

export interface PhraseRead {
  id: number;
  texte: string;
  created_at: string;          // ISO date
  theme?: string | null;
  niveau?: string | null;
  source?: string | null;
  langue?: string | null;
  auteur?: string | null;
  url_audio?: string | null;
}
