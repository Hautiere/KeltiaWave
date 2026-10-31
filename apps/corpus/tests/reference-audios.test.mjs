import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const exports = {};
vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/app/core/reference-audios.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, { exports });
const select = exports.selectReferenceAudios;
const audio = (id, patch = {}) => ({id, phrase_id:1, status:'approved', created_at:`2026-10-${String(id).padStart(2,'0')}`, validator_role:'teacher', ...patch});
test('both journeys select one reviewed reference per phrase in a stable order', () => {
  const rows = [audio(1), audio(2), audio(3, {phrase_id:2}), audio(4, {status:'pending'}), audio(5, {status:'rejected'})];
  assert.deepEqual(Array.from(select(rows), row=>row.id), [3,2]);
  assert.deepEqual(Array.from(select([...rows].reverse()), row=>row.id), [3,2]);
});
test('approval requires a teacher/admin review or the existing owner batch approval', () => {
  const rows = [audio(1,{validator_role:null}), audio(2,{validator_role:null,phrase_source:'common-voice',validation_comment:'Approbation en lot demandée par le propriétaire'}), audio(3,{validations:[{validator_role:'teacher',decision:'rejected'}]})];
  assert.deepEqual(Array.from(select(rows), row=>row.id), [2]);
});
