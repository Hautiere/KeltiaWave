import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import test from 'node:test';
import assert from 'node:assert/strict';
import { File } from 'node:buffer';
import {createRequire} from 'node:module';
const rx=createRequire(import.meta.url)('rxjs');

function makeSession(recordable = false) {
  const tracks = [{ kind: 'audio', stopped: false, stop() { this.stopped = true; }, addEventListener() {} },
    { kind: 'video', stopped: false, stop() { this.stopped = true; }, addEventListener() {} }];
  const stream = { getTracks: () => tracks, getAudioTracks: () => tracks.filter(track => track.kind === 'audio') };
  const sockets = [];
  const contexts = [];
  const nodes = [];
  const recorders = [];
  const timeouts = new Map();
  const intervals = new Map();
  let id = 0;
  class Socket {
    static OPEN = 1;
    readyState = 0;
    bufferedAmount = 0;
    sent = [];
    constructor() { sockets.push(this); }
    send(message) { this.sent.push(message); }
    close() { this.readyState = 3; }
    open() { this.readyState = 1; this.onopen(); }
    event(event) { this.onmessage({ data: JSON.stringify(event) }); }
  }
  class Context {
    sampleRate = 48000;
    closed = false;
    audioWorklet = { addModule: async () => {} };
    constructor() { contexts.push(this); }
    async resume() {}
    async close() { this.closed = true; }
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
  }
  class Node {
    port = {
      postMessage: command => {
        if (command === 'flush') {
          this.port.onmessage({ data: { pcm: new ArrayBuffer(4), level: .1 } });
          this.port.onmessage({ data: { flushed: true } });
        }
      },
    };
    constructor() { nodes.push(this); }
    connect() {}
    disconnect() {}
  }
  class Recorder {
    static isTypeSupported(type) { return type === 'audio/webm;codecs=opus'; }
    state = 'inactive';
    constructor(_stream, options) { this.mimeType = options.mimeType; recorders.push(this); }
    start() { this.state = 'recording'; }
    pause() { this.state = 'paused'; }
    resume() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      this.ondataavailable({ data: new Blob(['tail']) });
      this.onstop();
    }
  }
  const exports = {};
  const sandbox = {
    exports, URL, URLSearchParams, Error, ArrayBuffer, JSON, Promise, Blob, File, FormData,
    location: { hostname: '127.0.0.1', port: '4800', protocol: 'http:', origin: 'http://127.0.0.1:4800' },
    navigator: { mediaDevices: { getDisplayMedia: async () => stream } },
    AudioContext: Context, AudioWorkletNode: Node, WebSocket: Socket,
    MediaStream: class {},
    window: { isSecureContext: true, AudioWorkletNode: Node,
      setTimeout: callback => { timeouts.set(++id, callback); return id; },
      clearTimeout: key => timeouts.delete(key),
      setInterval: callback => { intervals.set(++id, callback); return id; },
      clearInterval: key => intervals.delete(key),
    },
    require: name => name === '@angular/core' ? { Injectable: () => target => target } : name==='rxjs'?rx:name==='@angular/common/http'?{HttpEventType:{UploadProgress:1,Response:4}}:{},
  };
  if (recordable) sandbox.MediaRecorder = Recorder;
  const code = ts.transpileModule(readFileSync(new URL('../src/live-audio.service.ts', import.meta.url), 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, experimentalDecorators: true },
  }).outputText;
  vm.runInNewContext(code, sandbox);
  const calls=[];const http={post:(...args)=>{calls.push(args);return rx.of({type:4,body:{text:'Bore da.'}});},get:(url)=>{calls.push([url]);return rx.of({estimated_seconds:4});}};
  return { service: new exports.LiveAudioService(http), calls, sockets, nodes, contexts, tracks, timeouts, intervals, sandbox, recorders };
}

async function openSession(session, events = [], language='br') {
  const pending = session.service.start(event => events.push(event), () => {}, () => {}, language);
  // Settle the capture and worklet setup promises without real timers or devices.
  for (let i = 0; i < 10 && !session.sockets.length; i++) await Promise.resolve();
  const socket = session.sockets[0];
  assert.ok(socket);
  socket.open();
  socket.event({ type: 'ready' });
  await pending;
  return socket;
}

test('sharing without audio releases all tracks and never opens a socket', async () => {
  const session = makeSession();
  session.tracks[0].kind = 'video';
  await assert.rejects(session.service.start(() => {}, () => {}, () => {}), /Aucun son partagé/);
  assert.ok(session.tracks.every(track => track.stopped));
  assert.equal(session.sockets.length, 0);
});

test('stop sends final PCM before stop control and releases the capture', async () => {
  const session = makeSession();
  const events = [];
  const socket = await openSession(session, events);
  await session.service.stop();
  assert.equal(JSON.parse(socket.sent[0]).sample_rate, 48000);
  assert.ok(socket.sent[1] instanceof ArrayBuffer);
  assert.equal(JSON.parse(socket.sent[2]).type, 'stop');
  assert.ok(session.tracks.every(track => track.stopped));
  assert.ok(session.contexts[0].closed);
  socket.event({ type: 'final', text: 'demat' });
  socket.event({ type: 'done' });
  assert.equal(events[0].text, 'demat');
  assert.equal(socket.readyState, 3);
  assert.equal(session.intervals.size, 0);
});

test('network failure keeps received text and stops capture', async () => {
  const session = makeSession();
  const events = [];
  const socket = await openSession(session, events);
  socket.event({ type: 'final', text: 'demat' });
  socket.onclose();
  assert.equal(events[0].text, 'demat');
  assert.equal(events[1].type, 'error');
  assert.ok(session.tracks.every(track => track.stopped));
  assert.equal(session.intervals.size, 0);
});

test('a cancelled share picker cannot attach a stale stream to a new session', async () => {
  const session = makeSession();
  let resolvePicker;
  session.sandbox.navigator.mediaDevices.getDisplayMedia = () => new Promise(resolve => { resolvePicker = resolve; });
  const pending = session.service.start(() => {}, () => {}, () => {});
  await session.service.stop();
  resolvePicker({ getTracks: () => session.tracks });
  await pending;
  assert.ok(session.tracks.every(track => track.stopped));
  assert.equal(session.sockets.length, 0);
});

test('Whisper audio includes the last chunk and follows pause and resume', async () => {
  const session = makeSession(true);
  const socket = await openSession(session);
  const recorder = session.recorders[0];
  recorder.ondataavailable({ data: new Blob(['first']) });
  assert.equal(session.service.whisperAudio, null);
  session.service.pause(true);
  assert.equal(recorder.state, 'paused');
  session.service.pause(false);
  assert.equal(recorder.state, 'recording');
  await session.service.stop();
  assert.equal(await session.service.whisperAudio.text(), 'firsttail');
  assert.equal(session.service.whisperAudio.name, 'keltiawave-live.webm');
  socket.event({ type: 'done' });
  session.service.destroy();
  assert.equal(session.service.whisperAudio, null);
});

test('audio size limit disables Whisper without interrupting Vosk', async () => {
  const session = makeSession(true);
  session.service.archiveLimit = 2;
  const socket = await openSession(session);
  session.recorders[0].ondataavailable({ data: new Blob(['too large']) });
  assert.equal(session.service.whisperAudio, null);
  assert.match(session.service.whisperAudioMessage, /limite/);
  assert.equal(socket.readyState, 1);
  session.service.destroy();
});

test('Welsh capture uses cy for the handshake, estimate and post-stop Whisper audio',async()=>{
  const session=makeSession(true);const socket=await openSession(session,[],'cy');
  assert.equal(JSON.parse(socket.sent[0]).language,'cy');
  await session.service.stop();socket.event({type:'done'});
  session.sandbox.navigator.mediaDevices.getDisplayMedia=async()=>{throw new Error('Cancelled next capture');};
  await assert.rejects(session.service.start(()=>{},()=>{},()=>{},'br'));
  await session.service.whisperEstimate(10);await session.service.improve();
  assert.match(session.calls[0][0],/lang=cy/);
  assert.equal(session.calls[1][1].get('language'),'cy');
});
