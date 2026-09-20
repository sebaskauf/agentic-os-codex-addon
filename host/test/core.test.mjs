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

test('windows .cmd shims are wrapped for cmd.exe with quoted arguments', async () => {
  await build({ entryPoints: ['src/platform.ts'], bundle: true, platform: 'node', format: 'cjs', outdir: tmp, outbase: 'src', outExtension: { '.js': '.cjs' } });
  const { wrapForCmd, supportedPlatform } = require(join(tmp, 'platform.cjs'));
  const wrapped = wrapForCmd('C:\\Users\\m\\AppData\\Roaming\\npm\\codex.cmd', ['--remote', 'ws://127.0.0.1:5000', '-C', 'C:\\My Vault'], 'cmd.exe');
  assert.equal(wrapped.file, 'cmd.exe');
  assert.deepEqual(wrapped.args, ['/d', '/s', '/c', '"C:\\Users\\m\\AppData\\Roaming\\npm\\codex.cmd --remote ws://127.0.0.1:5000 -C "C:\\My Vault""']);
  assert.throws(() => wrapForCmd('codex.cmd', ['a"b'], 'cmd.exe'));
  assert.equal(supportedPlatform(), process.platform === 'darwin' || process.platform === 'win32');
});

test('websocket bridge (Windows transport) guards the app-server with a capability token and serves a real TUI', { skip: process.platform === 'linux' }, async () => {
  process.env.AGENTIC_OS_CODEX_TRANSPORT = 'ws';
  await build({ entryPoints: ['src/codexBridge.ts', 'src/providers/codex.ts'], bundle: true, platform: 'node', format: 'cjs', outdir: join(tmp, 'ws'), outbase: 'src', outExtension: { '.js': '.cjs' } });
  const { startCodexBridge, TOKEN_ENV } = require(join(tmp, 'ws/codexBridge.cjs'));
  const { codexCommand } = require(join(tmp, 'ws/providers/codex.cjs'));
  const net = await import('node:net');
  const bridge = await startCodexBridge({ tabId: 'ws-fixture', launchId: 'test', cwd: tmp, onMetadata: () => {} });
  try {
    assert.match(bridge.remote, /^ws:\/\/127\.0\.0\.1:\d+$/);
    assert.equal(bridge.transport, 'ws');
    assert.equal(bridge.tuiArgs[0], '--remote-auth-token-env');
    assert.match(bridge.tuiEnv[TOKEN_ENV], /^[0-9a-f]{64}$/);
    const command = codexCommand({ cwd: tmp }, bridge.remote, TOKEN_ENV);
    assert.deepEqual(command.args.slice(0, 4), ['--remote', bridge.remote, '--remote-auth-token-env', TOKEN_ENV]);
    // Unauthenticated handshake through the bridge must be rejected by the app-server.
    const port = Number(bridge.remote.split(':').pop());
    const reply = await new Promise((resolve) => {
      const s = net.connect(port, '127.0.0.1'); let data = '';
      s.on('data', b => { data += b.toString('latin1'); });
      s.on('connect', () => s.write(`GET / HTTP/1.1\r\nHost: 127.0.0.1:${port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n`));
      setTimeout(() => { s.destroy(); resolve(data.split('\r\n')[0]); }, 1500);
    });
    assert.match(reply, /401/);
  } finally { bridge.dispose(); }
  // Fresh bridge: a real TUI with the token connects (101) — proves the whole Windows-style chain on this host.
  const bridge2 = await startCodexBridge({ tabId: 'ws-fixture-2', launchId: 'test', cwd: tmp, onMetadata: () => {} });
  try {
    const native = require(join(process.cwd(), 'native', `${process.platform}-${process.arch}`, 'lib/index.js'));
    const command = codexCommand({ cwd: tmp }, bridge2.remote, TOKEN_ENV);
    const child = native.spawn(command.file, command.args, { cwd: tmp, name: 'xterm-256color', cols: 100, rows: 30, env: { ...command.env, ...bridge2.tuiEnv } });
    let out = '';
    child.onData(t => { out += t; });
    await new Promise(r => setTimeout(r, 7000));
    child.kill();
    assert.match(out, /OpenAI Codex/);
    assert.notEqual(bridge2.identity.current.identityStatus, 'unavailable');
  } finally { bridge2.dispose(); delete process.env.AGENTIC_OS_CODEX_TRANSPORT; }
});
