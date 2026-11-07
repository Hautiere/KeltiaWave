/** Validation for phrase write forms; existing read contracts stay unchanged. */
export function isValidPhraseSourceUrl(value: string | null | undefined): boolean {
  const cleaned = (value || '').trim();
  if (!cleaned || cleaned.length > 2048 || !/^https?:\/\/[^/?#]/i.test(cleaned) || /[\\\s]/.test(cleaned)) return false;
  try {
    return !!new URL(cleaned).hostname;
  } catch {
    return false;
  }
}
