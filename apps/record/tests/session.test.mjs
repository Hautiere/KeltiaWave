import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {File} from 'node:buffer';

function session({offline=false,denied=false}={}) {
  const sockets=[],tracks=[],timers=new Map(),recorders=[];let id=0,microphones=0;
  class Socket {
    static OPEN=1;readyState=0;bufferedAmount=0;sent=[];
    constructor(url){this.url=url;sockets.push(this);}
    send(data){this.sent.push(data);}
    close(){this.readyState=3;}
    open(){this.readyState=1;this.onopen();}
    event(payload){this.onmessage?.({data:JSON.stringify(payload)});}
  }
  class Context {
    sampleRate=48000;
    async resume(){} async close(){}
    createMediaStreamSource(){return {connect(){},disconnect(){}};}
    createScriptProcessor(){return {connect(){},disconnect(){},onaudioprocess:null};}
  }
  class Recorder {
    static isTypeSupported(){return true;}
    state='inactive';mimeType='audio/webm';
    constructor(){recorders.push(this);}
    start(){this.state='recording';}
    stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['fixture'])});queueMicrotask(()=>this.onstop?.());}
  }
  const window={location:{hostname:'localhost',protocol:'http:'},AudioContext:Context,setTimeout:fn=>{timers.set(++id,fn);return id;},clearTimeout:id=>timers.delete(id),setInterval:fn=>{timers.set(++id,fn);return id;},clearInterval:id=>timers.delete(id)};
  const exports={};const code=ts.transpileModule(readFileSync(new URL('../src/record-app.component.ts',import.meta.url),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,experimentalDecorators:true}}).outputText;
  vm.runInNewContext(code,{exports,window,File,Blob,URL,URLSearchParams,Date,Float32Array,Int16Array,WebSocket:Socket,MediaRecorder:Recorder,
    location:{hostname:'localhost',protocol:'http:',search:''},localStorage:{getItem:()=>null},navigator:{onLine:!offline,mediaDevices:{getUserMedia:async()=>{microphones++;if(denied)throw new Error('Permission denied');const track={stopped:false,stop(){this.stopped=true;}};tracks.push(track);return {getTracks:()=>[track]};}}},
    require:name=>name==='@angular/core'?{Component:()=>target=>target}:{}
  });
  const calls=[];const api={wsBase:'ws://localhost:4400',transcribe:async(file,language)=>{calls.push(language);return {text:'Whisper result',removed_trailing_phrases:[],draft_prefix_preserved:false};},formatError:error=>error.message};
  const view=new exports.RecordAppComponent(api,{run:fn=>fn()});
  return {view,sockets,recorders,tracks,timers,calls,get microphones(){return microphones;}};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function start(s,language){s.view.language=language;const pending=s.view.startRecording();await tick();s.sockets.at(-1).open();s.sockets.at(-1).event({type:'ready'});await pending;}

test('Welsh microphone audio starts W2V live and sends a cy handshake on the frontend origin',async()=>{
 const s=session();await start(s,'cy');const ws=s.sockets[0];
 assert.equal(ws.url,'ws://localhost:4400/api/live/stream');assert.equal(JSON.parse(ws.sent[0]).language,'cy');assert.equal(s.view.directEngine,'W2V');
 s.view.processor.onaudioprocess({inputBuffer:{getChannelData:()=>new Float32Array([.2,-.2,.5,-.5])}});
 assert.ok(ws.sent[1] instanceof ArrayBuffer || Object.prototype.toString.call(ws.sent[1])==='[object ArrayBuffer]');
 ws.event({type:'partial',text:'Bore'});assert.equal(s.view.draft,'Bore');
 const stopping=s.view.stopRecording();assert.equal(s.view.finalizing,true);assert.equal(s.view.canUseWhisper,false);
 assert.equal(JSON.parse(ws.sent.at(-1)).type,'stop');ws.event({type:'final',text:'Bore da'});ws.event({type:'done'});await stopping;
 assert.equal(s.view.draft,'Bore da');assert.ok(s.view.audioFile.size>0);assert.equal(s.view.finalizing,false);assert.equal(s.view.canUseWhisper,true);
 s.view.language='br';await s.view.runWhisper();assert.deepEqual(s.calls,['cy']);assert.equal(s.view.draft,'Bore da');assert.equal(s.view.improved,'Whisper result');s.view.ngOnDestroy();
});
test('Breton keeps the local-origin Record Vosk endpoint and optional Whisper',async()=>{
 const s=session();await start(s,'br');assert.equal(s.sockets[0].url,'ws://localhost:4400/api/record/live');assert.equal(s.view.directEngine,'Vosk');assert.equal(s.calls.length,0);s.view.ngOnDestroy();
});
test('offline Welsh never starts a microphone and retains previous text',async()=>{
 const s=session({offline:true});s.view.language='cy';s.view.draft='Previous';await s.view.startRecording();assert.equal(s.microphones,0);assert.equal(s.view.draft,'Previous');assert.match(s.view.error,/Internet/);
});
test('denied microphone retains the prior transcript and releases the starting state',async()=>{
 const s=session({denied:true});s.view.draft='Previous';await s.view.startRecording();assert.equal(s.view.draft,'Previous');assert.equal(s.view.starting,false);assert.equal(s.view.recording,false);assert.equal(s.sockets.length,0);
});
test('language selection is locked through server finalization',async()=>{
 const s=session();await start(s,'cy');s.view.selectLanguage('br');assert.equal(s.view.language,'cy');
 const pending=s.view.stopRecording();s.view.selectLanguage('br');assert.equal(s.view.language,'cy');s.sockets[0].event({type:'done'});await pending;s.view.selectLanguage('br');assert.equal(s.view.language,'br');s.view.ngOnDestroy();
});
test('finalization timeouts preserve the recorded audio and received words',async()=>{
 const s=session();await start(s,'cy');const ws=s.sockets[0];ws.event({type:'final',text:'Bore da'});
 const pending=s.view.stopRecording();s.timers.get(s.view.finishTimer)();await pending;
 assert.equal(s.view.draft,'Bore da');assert.ok(s.view.audioFile.size>0);assert.match(s.view.error,/expiré/);assert.equal(s.view.finalizing,false);s.view.ngOnDestroy();
});
