import { isValidPhraseSourceUrl } from './phrase-provenance';

describe('Phrase provenance URL', () => {
  for (const url of ['https://example.org/source?lang=br#phrase', 'HTTP://example.org/path', '  https://example.org  ']) {
    it(`accepts ${url}`, () => expect(isValidPhraseSourceUrl(url)).toBeTrue());
  }
  for (const url of [null, undefined, '', '   ', 'ftp://example.org', 'javascript:alert(1)', 'https://', 'https:///path', 'https://exa mple.org', 'https://example.org:bad', 'https://example.org\\path']) {
    it(`rejects ${url}`, () => expect(isValidPhraseSourceUrl(url)).toBeFalse());
  }
  it('allows 2048 characters after trimming, but not 2049', () => {
    const url = 'https://example.org/' + 'a'.repeat(2048 - 'https://example.org/'.length);
    expect(isValidPhraseSourceUrl(`  ${url}  `)).toBeTrue();
    expect(isValidPhraseSourceUrl(url + 'a')).toBeFalse();
  });
});
