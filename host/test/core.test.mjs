import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
const tmp = mkdtempSync(join(tmpdir(), 'aos-codex-host-test-'));
process.env.CODEX_HOME = join(tmp, 'codex');
mkdirSync(process.env.CODEX_HOME);
writeFileSync(join(process.env.CODEX_HOME, 'review.config.toml'), 'developer_instructions = "Exact instructions äöü"\nmodel_reasoning_effort = "high"\n');
await build({ entryPoints: ['src/state.ts', 'src/sessionIdentity.ts', 'src/providers/codex.ts', 'src/codexProfile.ts', 'src/codexBridge.ts'], bundle: true, platform: 'node', format: 'cjs', outdir: tmp, outbase: 'src', outExtension: { '.js': '.cjs' } });
const require = createRequire(import.meta.url);
const { readSettings, resumableThread } = require(join(tmp, 'state.cjs'));
const { SessionIdentityObserver } = require(join(tmp, 'sessionIdentity.cjs'));
const { codexCommand, listCodexProfiles } = require(join(tmp, 'providers/codex.cjs'));
const { profileOverrides } = require(join(tmp, 'codexProfile.cjs'));
const A = '11111111-1111-4111-8111-111111111111';
const B = '22222222-2222-4222-8222-222222222222';
test('fresh state is opt-in and contains no session or personal default', () => {
  assert.deepEqual(readSettings(null), { enabled: false, sessions: [] });
});
test('untrusted saved identities cannot produce a resume command', () => {
  const parsed = readSettings({ enabled: 'true', sessions: [{ id: 'x', cwd: tmp, threadId: '--last', profile: '../../other' }] });
  assert.equal(parsed.enabled, false);
  assert.equal(parsed.sessions[0].threadId, undefined);
  assert.equal(parsed.sessions[0].profile, undefined);
  assert.throws(() => codexCommand({ cwd: tmp, nativeThreadId: '--last' }));
});
test('launch respects profile exactly without expanding member permissions or roots', () => {
  assert.deepEqual(listCodexProfiles(), ['review']);
  const command = codexCommand({ cwd: tmp, profile: 'review', nativeThreadId: A, dangerous: true }, 'unix:///tmp/example.sock');
  assert.deepEqual(command.args, ['-p', 'review', '--remote', 'unix:///tmp/example.sock', '--no-alt-screen', '-C', tmp, 'resume', A]);
  assert.ok(!Object.keys(command.env).some(k => k.startsWith('CLAUDE_CODE_') || k.startsWith('CLAUDECODE')));
  assert.deepEqual(profileOverrides('review'), ['-c', 'developer_instructions="Exact instructions äöü"', '-c', 'model_reasoning_effort="high"']);
});
test('only correlated latest native response can select a thread, not background agents', () => {
  const observer = new SessionIdentityObserver('pane', 'generation', () => {});
  observer.request({ id: 1, method: 'thread/start' });
  observer.request({ id: 2, method: 'thread/fork' });
  observer.response({ id: 1, result: { thread: { id: A } } });
  observer.response({ method: 'thread/started', params: { thread: { id: A } } });
  assert.equal(observer.current.nativeThreadId, undefined);
  observer.response({ id: 2, result: { thread: { id: B } } });
  assert.equal(observer.current.nativeThreadId, B);
});
test('observer failure invalidates prior native identity instead of resuming a stale session', () => {
  const observer = new SessionIdentityObserver('pane', 'generation', () => {});
  observer.request({ id: 1, method: 'thread/start' });
  observer.response({ id: 1, result: { thread: { id: A } } });
  observer.unavailable('broken transport');
  assert.equal(observer.current.nativeThreadId, undefined);
  assert.equal(observer.current.identityStatus, 'unavailable');
});
test('packaged macOS native terminal can spawn a harmless command', { skip: process.platform !== 'darwin' }, async () => {
  const native = require(join(process.cwd(), 'native', `darwin-${process.arch}`, 'lib/index.js'));
  const child = native.spawn('/usr/bin/printf', ['AOS_NATIVE_OK'], { cwd: tmp, name: 'xterm-256color', cols: 80, rows: 24, env: { PATH: '/usr/bin:/bin' } });
  let output = '';
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => { child.kill(); reject(new Error('PTY smoke timeout')); }, 5000);
    child.onData(text => { output += text; });
    child.onExit(({ exitCode }) => { clearTimeout(timeout); exitCode === 0 ? resolve() : reject(new Error(`Exit ${exitCode}`)); });
  });
  assert.match(output, /AOS_NATIVE_OK/);
});

test('real local Codex bridge opens private sockets without starting a model turn', { skip: process.platform !== 'darwin' }, async () => {
  const { startCodexBridge } = require(join(tmp, 'codexBridge.cjs'));
  const { existsSync, statSync } = await import('node:fs');
  const bridge = await startCodexBridge({ tabId: 'fixture', launchId: 'test', cwd: tmp, onMetadata: () => {} });
  try {
    const socket = bridge.remote.replace('unix://', '');
    assert.ok(existsSync(socket));
    assert.equal(statSync(socket).mode & 0o777, 0o600);
    assert.equal(bridge.identity.current.identityStatus, 'pending');
  } finally { bridge.dispose(); }
});

test('empty native threads are not offered as durable resume targets', () => {
  const observer = new SessionIdentityObserver('pane','g',()=>{});
  observer.request({ id: 1, method: 'thread/start' });
  observer.response({ id: 1, result: { thread: { id: A } } });
  assert.equal(resumableThread(observer.current), undefined);
  observer.response({ method: 'turn/started', params: { threadId: A } });
  assert.equal(resumableThread(observer.current), A);
});
