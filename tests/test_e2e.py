"""Install the real built payload into artificial member homes without opening apps."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_e2e", ROOT / "scripts/setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


@unittest.skipUnless((ROOT / "host/build/main.js").exists(), "Build host/ first")
class FullPackageTests(unittest.TestCase):
    def test_real_host_plus_role_skill_mcp_custom_base_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.sys, "platform", "darwin"):
            root = Path(tmp).resolve()
            home = root / "member"
            vault = home / "My Brain"
            base = vault / ".obsidian/plugins/agentic-os"
            base.mkdir(parents=True)
            (base / "manifest.json").write_text(json.dumps({"id": "agentic-os", "version": "custom-fork"}))
            (base / "main.js").write_bytes(b"customized community host")
            agents = home / ".claude/agents"
            agents.mkdir(parents=True)
            body = "Use my own writing voice.\nPreserve my chosen examples.\n"
            (agents / "writer.md").write_text("---\nname: writer\ndescription: My writer\n---\n" + body)
            skill = vault / ".claude/skills/research"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: research\ndescription: Research helper\n---\nRead primary sources.\n")
            script = skill / "check.sh"
            script.write_text("#!/bin/sh\nexit 0\n")
            os.chmod(script, 0o755)
            codex = home / ".codex"
            codex.mkdir()
            original = b'# member preferences\nmodel = "member-model"\n'
            (codex / "config.toml").write_bytes(original)
            plan = setup.make_plan(vault, home, "codex", ["writer"], ["research"], ["notion"])
            staged = setup.stage(plan, root / "private-plan")
            setup.apply(Path(staged["plan"]), staged["sha256"])
            self.assertEqual((base / "main.js").read_bytes(), b"customized community host")
            companion = base.parent / setup.PLUGIN_ID
            self.assertEqual((companion / "main.js").read_bytes(), (ROOT / "host/build/main.js").read_bytes())
            config = tomllib.loads((codex / "config.toml").read_text())
            self.assertEqual(config["model"], "member-model")
            self.assertEqual(config["mcp_servers"]["notion"]["url"], "https://mcp.notion.com/mcp")
            profile = tomllib.loads((codex / "writer.config.toml").read_text())
            self.assertEqual(profile["developer_instructions"], body)
            self.assertEqual((vault / ".agents/skills/research/check.sh").stat().st_mode & 0o777, 0o755)
            again = setup.make_plan(vault, home, "codex", ["writer"], ["research"], ["notion"])
            self.assertEqual(again["changes"], [])
            self.assertFalse((vault / ".obsidian/community-plugins.json").exists())
            self.assertFalse((codex / "auth.json").exists())
            setup.rollback(Path(staged["plan"]), staged["sha256"])
            self.assertEqual((codex / "config.toml").read_bytes(), original)
            self.assertFalse((companion / "main.js").exists())
            self.assertEqual((base / "main.js").read_bytes(), b"customized community host")


if __name__ == "__main__":
    unittest.main()
