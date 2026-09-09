import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from integrations.planner import build_changes, IntegrationError

class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home, self.vault = self.root / 'home', self.root / 'vault'
        self.home.mkdir()
        self.vault.mkdir()

    def put(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())

    def plan(self, agents=None, skills=None, mcps=None):
        return build_changes(self.home, self.vault, agents or [], skills or [], mcps or [])

    def apply(self, plan):
        for change in plan['changes']:
            self.put(Path(change['path']), change['after'])

    def agent(self, body=b'  Be exact.\r\n\r\n'):
        self.put(self.home / '.claude/agents/writer.md', b'---\r\nname: writer\r\ndescription: Write things\r\n---\r\n' + body)

    def test_no_selection_does_not_write(self):
        self.assertEqual(self.plan()['changes'], [])
        self.assertFalse((self.home / '.codex').exists())

    def test_exact_prompt_and_idempotence(self):
        body = b'\r\n  Preserve "all" whitespace.\r\n\r\n'
        self.agent(body)
        result = self.plan(agents=['writer'])
        self.assertFalse((self.home / '.codex').exists())
        self.apply(result)
        for path in [self.home / '.codex/writer.config.toml', self.home / '.codex/agents/writer.toml']:
            self.assertEqual(tomllib.loads(path.read_text())['developer_instructions'].encode(), body)
        self.assertEqual(self.plan(agents=['writer'])['changes'], [])

    def test_preserves_unmanaged_config_and_profile_fields(self):
        self.agent()
        original = '# Keep this comment\nmodel = "member-model"\n[features]\ncustom = true\n'
        self.put(self.home / '.codex/config.toml', original)
        self.put(self.home / '.codex/writer.config.toml', 'model = "role-model"\n[tui]\ntheme = "light"\n')
        self.apply(self.plan(agents=['writer']))
        self.assertTrue((self.home / '.codex/config.toml').read_text().startswith(original))
        profile = self.home / '.codex/writer.config.toml'
        self.assertEqual(tomllib.loads(profile.read_text())['tui']['theme'], 'light')
        self.agent(b'Updated prompt\n')
        self.apply(self.plan(agents=['writer']))
        self.assertEqual(tomllib.loads(profile.read_text())['model'], 'role-model')
        self.assertTrue((self.home / '.codex/config.toml').read_text().startswith(original))

    def test_modified_managed_block_fails(self):
        self.agent()
        self.apply(self.plan(agents=['writer']))
        path = self.home / '.codex/writer.config.toml'
        self.put(path, path.read_text().replace('Be exact.', 'Local override.'))
        with self.assertRaises(IntegrationError):
            self.plan(agents=['writer'])

    def test_unowned_prompt_collision_fails(self):
        self.agent()
        self.put(self.home / '.codex/writer.config.toml', 'developer_instructions = "Private role"\n')
        with self.assertRaises(IntegrationError):
            self.plan(agents=['writer'])

    def test_selection_does_not_remove_existing(self):
        self.agent()
        self.apply(self.plan(agents=['writer']))
        self.apply(self.plan(mcps=['notion']))
        config = tomllib.loads((self.home / '.codex/config.toml').read_text())
        self.assertIn('writer', config['agents'])
        self.assertIn('notion', config['mcp_servers'])
        self.assertEqual(self.plan(mcps=['notion'])['changes'], [])

    def test_paths_traversal_and_symlinks(self):
        with self.assertRaises(IntegrationError):
            self.plan(agents=['../evil'])
        target = self.home / '.claude/agents'
        target.parent.mkdir()
        target.symlink_to(self.vault, target_is_directory=True)
        with self.assertRaises(IntegrationError):
            self.plan(agents=['writer'])

    def test_secret_mcp_not_copied_or_reported(self):
        secret = 'VERY_PRIVATE_FIXTURE_TOKEN'
        self.put(self.vault / '.mcp.json', json.dumps({'mcpServers': {
            'secret': {'url': 'https://example.com/mcp', 'headers': {'Authorization': secret}},
            'query': {'url': f'https://example.com/mcp?token={secret}'},
            'path': {'url': f'https://example.com/{secret}'},
            'stdio': {'command': 'x', 'env': {'TOKEN': secret}},
        }}))
        result = self.plan(mcps=['secret','query','path','stdio'])
        self.assertEqual(result['changes'], [])
        self.assertNotIn(secret, repr(result))
        self.assertTrue(all(x['state'] == 'manual-setup' for x in result['statuses']))

    def test_validated_remote_and_env_reference(self):
        self.put(self.vault / '.mcp.json', json.dumps({'mcpServers': {'custom': {
            'url': 'https://example.com/mcp', 'type': 'http', 'bearer_token_env_var': 'MY_SERVICE_TOKEN'}}}))
        self.apply(self.plan(mcps=['custom', 'linear']))
        config = tomllib.loads((self.home / '.codex/config.toml').read_text())
        self.assertEqual(config['mcp_servers']['custom']['bearer_token_env_var'], 'MY_SERVICE_TOKEN')
        self.assertEqual(config['mcp_servers']['linear']['url'], 'https://mcp.linear.app/mcp')

    def test_skill_copy_reuse_and_nested_symlink_rejection(self):
        self.put(self.home / '.claude/skills/write/SKILL.md', '# Write\n')
        self.apply(self.plan(skills=['write']))
        self.assertEqual(self.plan(skills=['write'])['changes'], [])
        (self.vault / '.agents/skills/write/secret').symlink_to(self.home)
        with self.assertRaises(IntegrationError):
            self.plan(skills=['write'])

    def test_existing_disabled_mcp_reused_without_enabling(self):
        self.put(self.home / '.codex/config.toml', '[mcp_servers.notion]\nurl = "https://mcp.notion.com/mcp"\nenabled = false\n')
        result = self.plan(mcps=['notion'])
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['statuses'][0]['state'], 'existing-disabled')

    def test_conflicting_existing_mcp_is_not_overwritten(self):
        self.put(self.home / '.codex/config.toml', '[mcp_servers.notion]\nurl = "https://different.example/mcp"\n')
        with self.assertRaises(IntegrationError):
            self.plan(mcps=['notion'])

    def test_malformed_remote_url_is_safe_manual_setup(self):
        self.put(self.vault / '.mcp.json', json.dumps({'mcpServers': {'broken': {'url': 'https://[broken/mcp'}}}))
        result = self.plan(mcps=['broken'])
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['statuses'][0]['state'], 'manual-setup')

    def test_new_skill_preserves_executable_mode(self):
        self.put(self.home / '.claude/skills/write/SKILL.md', '# Write\n')
        script = self.home / '.claude/skills/write/scripts/run.sh'
        self.put(script, '#!/bin/sh\nexit 0\n')
        script.chmod(0o751)
        result = self.plan(skills=['write'])
        change = next(item for item in result['changes'] if item['path'].endswith('run.sh'))
        self.assertEqual(change['mode'], 0o751)

    def test_invalid_config_error_does_not_echo_secret(self):
        secret = 'VERY_PRIVATE_FIXTURE_TOKEN'
        self.put(self.home / '.codex/config.toml', secret)
        with self.assertRaises(IntegrationError) as ctx:
            self.plan(mcps=['notion'])
        self.assertNotIn(secret, str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
