import { build } from 'esbuild';
import { builtinModules } from 'node:module';
import { mkdir, cp, copyFile, readFile, writeFile } from 'node:fs/promises';
await mkdir('build', { recursive: true });
await build({ entryPoints: ['src/main.ts'], bundle: true, platform: 'node', format: 'cjs', target: 'es2022', external: ['obsidian', 'electron', 'node-pty', ...builtinModules, ...builtinModules.map(x => 'node:' + x)], outfile: 'build/main.js' });
await copyFile('manifest.json', 'build/manifest.json');
const terminalCss = await readFile('node_modules/@xterm/xterm/css/xterm.css', 'utf8');
const ownCss = await readFile('styles.css', 'utf8');
await writeFile('build/styles.css', terminalCss + '\n' + ownCss);
await cp('native', 'build/native', { recursive: true });
await copyFile('src/vendor/smol-toml/LICENSE', 'build/LICENSE-smol-toml');
await copyFile('node_modules/@xterm/xterm/LICENSE', 'build/LICENSE-xterm');
await copyFile('node_modules/@xterm/addon-fit/LICENSE', 'build/LICENSE-xterm-addon-fit');
console.log('Built host/build only. No vault, settings or live plugin touched.');
await mkdir('build/licenses', {recursive:true});
for (const [src,dest] of [['node_modules/@xterm/xterm/LICENSE','xterm.txt'],['node_modules/@xterm/addon-fit/LICENSE','xterm-addon-fit.txt'],['src/vendor/smol-toml/LICENSE','smol-toml.txt']]) await copyFile(src,'build/licenses/'+dest);
const { readdir, stat } = await import('node:fs/promises');
const { createHash } = await import('node:crypto');
async function walk(dir, prefix = '') {
  const files = [];
  for (const name of (await readdir(dir)).sort()) {
    if (name === 'build-manifest.json') continue;
    const full = dir + '/' + name, relative = prefix + name, info = await stat(full);
    if (info.isDirectory()) files.push(...await walk(full, relative + '/'));
    else files.push({ path: relative, sha256: createHash('sha256').update(await readFile(full)).digest('hex'), mode: info.mode & 0o777, bytes: info.size });
  }
  return files;
}
await writeFile('build/build-manifest.json', JSON.stringify({ version: 1, pluginId: 'agentic-os-codex', files: await walk('build') }, null, 2) + '\n');
