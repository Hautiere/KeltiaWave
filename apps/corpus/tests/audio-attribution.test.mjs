import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const exports = {};
vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/app/core/audio-attribution.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, { exports });
const { audioAttribution } = exports;

test('a contributor owns their recording even on a Common Voice phrase', () => {
  assert.equal(audioAttribution({ origin: 'user', contributor_name: '  Fañch  ', phrase_source: 'suggested' }, 'common-voice'), 'Fañch');
});
test('an anonymous recording is attributed to Inconnu, including older uploads', () => {
  for (const name of [null, undefined, '', '   ']) {
    assert.equal(audioAttribution({ origin: 'user', contributor_name: name }, 'common-voice'), 'Inconnu');
  }
  assert.equal(audioAttribution({}, 'common-voice'), 'Inconnu');
});
test('dataset recordings keep their imported source', () => {
  assert.equal(audioAttribution({ origin: 'dataset', contributor_name: 'Locuteur' }, 'common-voice'), 'Common Voice');
  assert.equal(audioAttribution({ origin: 'dataset', phrase_source: 'Collection' }), 'Collection');
});

test('a validated Mamm voice keeps her name rather than the Common Voice phrase origin', () => {
  assert.equal(audioAttribution({origin:'user', contributor_name:'Mamm', phrase_source:'suggested'}, 'common-voice'), 'Mamm');
});
test('an imported audio uses its own source before the source of the text', () => {
  assert.equal(audioAttribution({origin:'dataset', phrase_source:'common-voice'}, 'Collection'), 'Common Voice');
});
