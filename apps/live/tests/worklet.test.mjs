import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';

function makeProcessor() {
  const messages = [];
  let Processor;
  const context = {
    AudioWorkletProcessor: class { port = { postMessage: value => messages.push(value) }; },
    registerProcessor: (_name, constructor) => { Processor = constructor; },
    Int16Array, Math,
  };
  vm.runInNewContext(readFileSync(new URL('../public/live-pcm-worklet.js', import.meta.url), 'utf8'), context);
  const processor = new Processor();
  return { processor, messages, command: data => processor.port.onmessage({ data }) };
}

test('stereo audio becomes signed mono PCM16 without monitoring output', () => {
  const { processor, messages, command } = makeProcessor();
  command('resume');
  processor.process([[new Float32Array([1, -1, .5]), new Float32Array([1, -1, -.5])]]);
  command('flush');
  assert.deepEqual([...new Int16Array(messages[0].pcm)], [32767, -32768, 0]);
  assert.equal(messages[0].level, 1);
  assert.equal(messages[1].flushed, true);
});

test('pause prevents new audio capture and resume retains block boundaries', () => {
  const { processor, messages, command } = makeProcessor();
  command('pause');
  processor.process([[new Float32Array(128).fill(.5)]]);
  assert.equal(messages.length, 0);
  command('resume');
  for (let i = 0; i < 16; i++) processor.process([[new Float32Array(128).fill(.5)]]);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].pcm.byteLength, 4096);
  command('flush');
  assert.equal(messages.length, 2);
  assert.equal(messages[1].flushed, true);
});
