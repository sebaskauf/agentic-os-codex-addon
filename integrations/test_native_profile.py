"""Explicit offline native-loader test. No valid model provider is configured."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from integrations.planner import build_changes


@unittest.skipUnless(os.environ.get('AOS_TEST_NATIVE_CODEX') == '1',
                     'Opt in to the installed CLI check with AOS_TEST_NATIVE_CODEX=1')
class NativeProfileTest(unittest.TestCase):
    def test_native_profile_file_layer_is_loaded(self):
        binary = shutil.which('codex')
        self.assertIsNotNone(binary, 'Install Codex CLI before running native integration checks')
        with tempfile.TemporaryDirectory(prefix='aos-native-profile-') as temporary:
            root = Path(temporary).resolve()
            home, vault = root / 'home', root / 'vault'
            roles = home / '.claude/agents'
            roles.mkdir(parents=True)
            vault.mkdir()
            (roles / 'fixture.md').write_text('---\nname: fixture\ndescription: Offline role\n---\nKeep this role unchanged.\n')
            for change in build_changes(home, vault, ['fixture'], [], [])['changes']:
                target = Path(change['path'])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(change['after'])
            codex_home = home / '.codex'
            base = codex_home / 'config.toml'
            profile = codex_home / 'fixture.config.toml'
            # Nonexistent providers force an early config error before any model
            # initialization or network attempt. Different markers reveal which
            # layer was actually loaded by the native CLI.
            base.write_text('model_provider = "aos-offline-base-marker"\n' + base.read_text())
            profile.write_text('model_provider = "aos-offline-profile-marker"\n' + profile.read_text())
            env = {key: value for key, value in os.environ.items()
                   if not any(term in key.upper() for term in ('TOKEN', 'API_KEY', 'AUTH'))}
            env.update(HOME=str(home), CODEX_HOME=str(codex_home))
            for name, marker in [('fixture', 'aos-offline-profile-marker'),
                                 ('missing-role', 'aos-offline-base-marker')]:
                result = subprocess.run([binary, 'exec', '-p', name, '--skip-git-repo-check', ''],
                                        cwd=vault, env=env, stdin=subprocess.DEVNULL,
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f'Model provider `{marker}` not found', result.stderr)


if __name__ == '__main__':
    unittest.main()
