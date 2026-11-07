import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const modules = new Map();
function load(url) {
  if (modules.has(url.href)) return modules.get(url.href);
  const exports = {}; modules.set(url.href, exports);
  const code = ts.transpileModule(readFileSync(url, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  vm.runInNewContext(code, { exports, URLSearchParams, require: path => load(new URL(path + '.ts', url)) });
  return exports;
}
const { filterExplorerPhrases: filter, initialExplorerState: initial, komzInterface: mode } = load(new URL('../src/app/pages-v2/record/explorer/komz-explorer.model.ts', import.meta.url));
const phrases = [
 { id: 1, texte: 'Demat !', theme: 'rencontres', subdomain: 'Saluer & prendre congé', niveau: 'A1', traduction_fr: 'Bonjour !', traduction_en: 'Hello!', traduction_cy: 'Helo!' },
 { id: 2, texte: 'Kenavo !', theme: 'rencontres', subdomain: 'saluer-et-prendre-conge', niveau: 'A2', traduction_fr: 'Au revoir !' },
 { id: 3, texte: "Petra eo da anv ?", theme: 'rencontres', subdomain: null, niveau: null, traduction_fr: 'Comment t’appelles-tu ? Quel est ton prénom ?' },
 { id: 4, texte: 'An ti.', theme: 'vie-quotidienne', niveau: 'A1' },
 { id: 5, texte: 'Nouveau texte sans voix.', theme: 'rencontres', subdomain: 'se-presenter', niveau: 'B1' },
];
const refs = new Set([1, 2, 3, 4]);
const ids = values => Array.from(values, value => value.id);
test('filters combine audio, subdomain aliases and actual level without losing unclassified phrases', () => {
 assert.deepEqual(ids(filter(phrases, refs, initial())), [1, 2, 3]);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), subdomain: 'saluer-et-prendre-conge', level: 'A2' })), [2]);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), subdomain: '__unclassified__', level: 'unrated' })), [3]);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), level: 'B1' })), []);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), level: 'B1', onlyWithAudio: false })), [5]);
});
test('search accepts accents, apostrophe variants and translations without mutating corpus', () => {
 const before = JSON.stringify(phrases);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), search: 'helo' })), [1]);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), search: "t'appelles" })), [3]);
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), search: 'prenom' })), [3]);
 assert.equal(JSON.stringify(phrases), before);
});
test('legacy domain aliases still count under the current theme', () => {
 assert.deepEqual(ids(filter(phrases, refs, { ...initial(), theme: 'maison-quotidien' })), [4]);
});
test('explicit classic URL always overrides modern storage and refresh is reversible', () => {
 assert.equal(mode('?interface=classic&phraseId=3', 'modern'), 'classic');
 assert.equal(mode('?interface=modern', 'classic'), 'modern');
 assert.equal(mode('', 'classic'), 'classic');
 assert.equal(mode('', null), 'modern');
 assert.equal(mode('?interface=invalid', 'classic'), 'classic');
});

const { mobileSubdomainLabel } = load(new URL('../src/app/pages-v2/record/explorer/komz-explorer.model.ts', import.meta.url));
test('mobile subdomain captions use balanced lines and at most four words', () => {
 assert.equal(mobileSubdomainLabel('Greetings & farewells'), 'Greetings\n& farewells');
 const label = mobileSubdomainLabel('Where you are from & where you live');
 assert.equal(label.replace(/\n/g, ' ').split(/\s+/).length, 4);
 assert.equal(label.split('\n').length, 2);
 assert.ok(label.endsWith('…'));
 assert.equal(mobileSubdomainLabel('All'), 'All');
});
