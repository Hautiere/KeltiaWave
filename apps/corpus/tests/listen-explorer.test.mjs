import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

function loadExplorer() {
  const modules = new Map();
  const decorator = () => () => {};
  class EventEmitter {
    values = [];
    emit(value) { this.values.push(value); }
  }
  function load(url) {
    if (modules.has(url.href)) return modules.get(url.href);
    const exports = {};
    modules.set(url.href, exports);
    const code = ts.transpileModule(readFileSync(url, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, experimentalDecorators: true },
    }).outputText;
    vm.runInNewContext(code, { exports, URLSearchParams, require(path) {
      if (path === '@angular/core') return { Component: decorator, Input: decorator, Output: decorator, ViewChild: decorator, EventEmitter };
      if (path.startsWith('@angular/')) return {};
      if (path.endsWith('i18n.service')) return {};
      if (path.endsWith('mobile-tools')) return { mobileToolLinks: () => ({}), mobileLabel: key => key };
      return load(new URL(path + '.ts', url));
    } });
    return exports;
  }
  const { KomzExplorerComponent } = load(new URL('../src/app/pages-v2/record/explorer/komz-explorer.component.ts', import.meta.url));
  const explorer = new KomzExplorerComponent({ translate: key => key });
  explorer.phrases = [
    { id: 1, texte: 'Demat', theme: 'rencontres', niveau: 'A1' },
    { id: 2, texte: 'Kenavo', theme: 'rencontres', niveau: 'A1' },
  ];
  explorer.references = [{ id: 10, phrase_id: 1, contributor_name: 'Yann', origin: 'user' }];
  const audio = { src: '', play: async () => {}, pause() {}, removeAttribute() {}, load() {} };
  explorer.player = { nativeElement: audio };
  return { explorer, audio };
}

test('Listen only offers phrases with references, including after filter changes', () => {
  const { explorer } = loadExplorer();
  explorer.experience = 'listen';
  explorer.state.onlyWithAudio = false;
  explorer.ngOnChanges();
  assert.deepEqual(Array.from(explorer.results, phrase => phrase.id), [1]);
  explorer.change({ onlyWithAudio: false });
  assert.equal(explorer.view.onlyWithAudio, true);
  assert.equal(explorer.referenceName(explorer.phrases[0]), 'Yann');
});

test('Listen unlocks practice only after the reference ends and stops on filtering', async () => {
  const { explorer, audio } = loadExplorer();
  explorer.experience = 'listen';
  explorer.ngOnChanges();
  const phrase = explorer.phrases[0];
  explorer.startPractice(phrase);
  assert.equal(explorer.practice.values.length, 0);
  await explorer.play(phrase);
  assert.equal(audio.src, '/api/audios/10/file');
  assert.equal(explorer.canRepeat(phrase), false);
  explorer.change({ level: 'A1' });
  assert.equal(explorer.playingId, null);
  explorer.endedAudio();
  assert.equal(explorer.canRepeat(phrase), false);
  await explorer.play(phrase);
  explorer.endedAudio();
  assert.equal(explorer.canRepeat(phrase), true);
  explorer.startPractice(phrase);
  assert.equal(explorer.practice.values[0], phrase);
});

test('Komz opens practice without listening and never starts reference playback', async () => {
  const { explorer, audio } = loadExplorer();
  explorer.ngOnChanges();
  let plays = 0;
  audio.play = async () => { plays++; };
  await explorer.play(explorer.phrases[0]);
  assert.equal(plays, 0);
  explorer.startPractice(explorer.phrases[0]);
  assert.equal(explorer.practice.values.length, 1);
});

test('mobile tab arrows follow horizontal overflow and scroll position', () => {
  const { explorer } = loadExplorer();
  const tabs = { scrollLeft: 0, clientWidth: 250, scrollWidth: 500 };
  explorer.toolTabs = { nativeElement: tabs };
  explorer.updateTabsOverflow();
  assert.equal(explorer.tabsCanGoBack, false);
  assert.equal(explorer.tabsCanGoForward, true);
  tabs.scrollLeft = 250;
  explorer.updateTabsOverflow();
  assert.equal(explorer.tabsCanGoBack, true);
  assert.equal(explorer.tabsCanGoForward, false);
  tabs.scrollLeft = 0;
  tabs.clientWidth = 500;
  explorer.updateTabsOverflow();
  assert.equal(explorer.tabsCanGoBack, false);
  assert.equal(explorer.tabsCanGoForward, false);
});
