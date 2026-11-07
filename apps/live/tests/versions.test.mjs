import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import test from 'node:test';
import assert from 'node:assert/strict';

function component(improve) {
  const exports = {};
  const timers = new Map();
  let now = 0;
  const code = ts.transpileModule(readFileSync(new URL('../src/live-app.component.ts', import.meta.url), 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, experimentalDecorators: true },
  }).outputText;
  vm.runInNewContext(code, {
    exports,
    Date: { now: () => now },
    window: { setInterval: callback => { timers.set(1, callback); return 1; }, clearInterval: id => timers.delete(id) },
    location: { hostname: '127.0.0.1' },
    requestAnimationFrame: callback => callback(),
    require: () => ({ Component: () => target => target, ViewChild: () => () => {} }),
  });
  const instance = new exports.LiveAppComponent({ whisperAudio: {}, whisperEstimate: async () => 10, improve }, {});
  instance.segments = ['demat deoc’h'];
  instance.whisperAvailable = true;
  instance.testTimers = timers;
  instance.advance = seconds => { now += seconds * 1000; for (const tick of timers.values()) tick(); };
  return instance;
}

test('Whisper creates a selectable version without overwriting Vosk', async () => {
  const view = component(async () => ({ text: 'Demat deoc’h.' }));
  await view.improve();
  assert.equal(view.version, 'whisper');
  assert.equal(view.text, 'Demat deoc’h.');
  view.version = 'vosk';
  assert.equal(view.text, 'demat deoc’h');
  assert.equal(view.improving, false);
});

test('failed or empty Whisper results preserve Vosk and allow retry', async () => {
  for (const improve of [async () => { throw new Error('offline'); }, async () => ({ text: ' ' })]) {
    const view = component(improve);
    await view.improve();
    assert.equal(view.text, 'demat deoc’h');
    assert.equal(view.whisperText, null);
    assert.ok(view.whisperError);
    assert.equal(view.busy, false);
  }
});


test('Whisper separates upload from estimated processing and keeps waiting when estimate expires', async () => {
  let finish;
  let upload;
  const view = component(callback => { upload = callback; return new Promise(resolve => { finish = resolve; }); });
  const pending = view.improve();
  await Promise.resolve();
  upload(40);
  assert.equal(view.whisperUpload, 40);
  assert.equal(view.whisperProcessing, false);
  upload(100);
  view.advance(5);
  assert.equal(view.whisperProcessing, true);
  assert.equal(view.whisperProgress, 50);
  assert.equal(view.whisperRemainingTime, '00:05');
  view.advance(10);
  assert.equal(view.whisperIndeterminate, true);
  assert.equal(view.whisperElapsedTime, '00:15');
  assert.equal(view.whisperProgress, 99);
  assert.equal(view.improving, true);
  finish({ text: 'Demat.' });
  await pending;
  assert.equal(view.testTimers.size, 0);
  assert.equal(view.improving, false);
});

test('failed Whisper processing clears its progress timer and preserves the draft', async () => {
  const view = component(async upload => { upload(100); throw new Error('offline'); });
  await view.improve();
  assert.equal(view.testTimers.size, 0);
  assert.equal(view.text, 'demat deoc’h');
  assert.equal(view.busy, false);
});
