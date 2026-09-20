import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("setup", Path(__file__).resolve().parents[1] / "scripts/setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.vault = self.home / "Member Vault"
        self.vault.mkdir(parents=True)
        self.platform = patch.object(setup.sys, "platform", "darwin")
        self.platform.start()

    def tearDown(self):
        self.platform.stop()
        self.temp.cleanup()

    def plan(self, changes, name="stage"):
        return setup.stage({"inventory": {"vault": str(self.vault), "home": str(self.home)},
                            "mode": "codex", "changes": changes, "statuses": [], "manual_steps": []}, self.root / name)

    def change(self, path, after, before=None):
        return {"path": str(path), "before": before, "after": after, "kind": "fixture"}

    def target(self, name="config.toml"):
        return self.home / ".codex" / name

    def test_apply_idempotent_and_rollback_preserves_original(self):
        path = self.target()
        path.parent.mkdir()
        path.write_bytes(b"member-owned\n")
        os.chmod(path, 0o640)
        p = self.plan([self.change(path, b"member-owned\nnew-field\n", path.read_bytes()),
                       self.change(self.target("aos.md"), b"exact role body")])
        folder = Path(p["plan"])
        self.assertEqual(setup.apply(folder, p["sha256"])["state"], "applied")
        self.assertEqual(setup.apply(folder, p["sha256"])["state"], "already-applied")
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        setup.rollback(folder, p["sha256"])
        self.assertEqual(path.read_bytes(), b"member-owned\n")
        self.assertFalse(self.target("aos.md").exists())
        self.assertEqual(len(list((folder / "rollback-archive").iterdir())), 1)
        self.assertEqual(setup.rollback(folder, p["sha256"])["state"], "already-rolled-back")

    def test_preflight_conflict_prevents_all_writes(self):
        first, second = self.target("first"), self.target("second")
        p = self.plan([self.change(first, b"a"), self.change(second, b"b")])
        second.parent.mkdir()
        second.write_bytes(b"member changed this")
        with self.assertRaisesRegex(setup.SetupError, "changed since inspection"):
            setup.apply(Path(p["plan"]), p["sha256"])
        self.assertFalse(first.exists())

    def test_rollback_refuses_later_member_edits(self):
        path = self.target()
        p = self.plan([self.change(path, b"installed")])
        setup.apply(Path(p["plan"]), p["sha256"])
        path.write_bytes(b"new member work")
        with self.assertRaisesRegex(setup.SetupError, "User changed"):
            setup.rollback(Path(p["plan"]), p["sha256"])
        self.assertEqual(path.read_bytes(), b"new member work")

    def test_changed_manifest_and_payload_rejected(self):
        p = self.plan([self.change(self.target(), b"test")])
        folder = Path(p["plan"])
        with self.assertRaisesRegex(setup.SetupError, "Plan hash"):
            setup.apply(folder, "wrong")
        (folder / "payload/0000.bin").write_bytes(b"tampered")
        with self.assertRaisesRegex(setup.SetupError, "Payload hash"):
            setup.apply(folder, p["sha256"])
        self.assertFalse(self.target().exists())

    def test_scope_and_symlinks_rejected(self):
        p = self.plan([self.change(self.vault / "important.md", b"no")])
        with self.assertRaisesRegex(setup.SetupError, "outside"):
            setup.apply(Path(p["plan"]), p["sha256"])
        (self.home / ".codex").symlink_to(self.root, target_is_directory=True)
        p = self.plan([self.change(self.target(), b"no")], "symlink-stage")
        with self.assertRaisesRegex(setup.SetupError, "Symlink"):
            setup.apply(Path(p["plan"]), p["sha256"])

    def test_auth_files_are_never_written(self):
        p = self.plan([self.change(self.target("auth.json"), b"no")])
        with self.assertRaisesRegex(setup.SetupError, "authentication"):
            setup.apply(Path(p["plan"]), p["sha256"])

    def test_empty_claude_only_without_codex_or_base(self):
        with patch.object(setup.shutil, "which", return_value=None):
            plan = setup.make_plan(self.vault, self.home, "claude-only", [], [], [])
        self.assertEqual(plan["changes"], [])
        self.assertEqual(list(self.vault.iterdir()), [])

    def base_plugin(self):
        base = self.vault / ".obsidian/plugins/agentic-os"
        base.mkdir(parents=True)
        (base / "manifest.json").write_text(json.dumps({"id": "agentic-os", "version": "0.2.2"}))
        (base / "main.js").write_bytes(b"public build")
        repo = self.root / "bundle"
        build = repo / "host/build"
        build.mkdir(parents=True)
        (build / "manifest.json").write_text(json.dumps({"id": setup.PLUGIN_ID}))
        (build / "main.js").write_bytes(b"companion build")
        return repo

    def test_linux_can_inspect_but_not_install(self):
        with patch.object(setup.sys, "platform", "linux"), patch.object(setup.shutil, "which", return_value=None):
            self.assertFalse(setup.inventory(self.vault, self.home)["supported_host_install"])
            with self.assertRaisesRegex(setup.SetupError, "macOS and Windows"):
                setup.make_plan(self.vault, self.home, "codex", [], [], [])

    def test_windows_plans_host_and_shared_brain(self):
        repo = self.base_plugin()
        (self.vault / "CLAUDE.md").write_text("# Mein Vault\n")
        (self.vault / "memory").mkdir()
        (self.vault / "memory/MEMORY.md").write_text("- [x](x.md)\n")
        with patch.object(setup.sys, "platform", "win32"), patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "ROOT", repo):
            info = setup.inventory(self.vault, self.home)
            self.assertTrue(info["supported_host_install"])
            self.assertTrue(info["brain"]["memory_index"])
            plan = setup.make_plan(self.vault, self.home, "codex", [], [], [])
        paths = {Path(c["path"]).name for c in plan["changes"]}
        self.assertIn("main.js", paths)
        self.assertIn("AGENTS.md", paths)
        agents = next(c for c in plan["changes"] if Path(c["path"]).name == "AGENTS.md")
        text = agents["after"].decode()
        self.assertIn("memory/MEMORY.md", text)
        self.assertIn("<!-- BEGIN AGENTIC OS CODEX ADDON -->", text)
        config = next(c for c in plan["changes"] if Path(c["path"]).name == "config.toml")
        self.assertIn('trust_level = "trusted"', config["after"].decode())
        self.assertNotIn("writable_roots", config["after"].decode())
        self.assertEqual([s["kind"] for s in plan["statuses"]], ["brain"])

    def test_brain_outside_vault_adds_writable_root_and_pointer(self):
        repo = self.base_plugin()
        brain = self.home / "Second Brain"
        (brain / "memory").mkdir(parents=True)
        (brain / "memory/MEMORY.md").write_text("- [a](a.md)\n")
        with patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "ROOT", repo):
            plan = setup.make_plan(self.vault, self.home, "codex", [], [], [], brain=brain)
        config = next(c for c in plan["changes"] if Path(c["path"]).name == "config.toml")["after"].decode()
        self.assertIn("writable_roots", config)
        self.assertIn(brain.as_posix(), config)
        agents = next(c for c in plan["changes"] if Path(c["path"]).name == "AGENTS.md")["after"].decode()
        self.assertIn(brain.as_posix(), agents)
        with patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "ROOT", repo):
            without = setup.make_plan(self.vault, self.home, "codex", [], [], [], shared_brain=False)
        self.assertNotIn("AGENTS.md", {Path(c["path"]).name for c in without["changes"]})

    def test_agents_md_keeps_member_text_and_applies_in_scope(self):
        repo = self.base_plugin()
        (self.vault / "AGENTS.md").write_text("# Meine eigenen Regeln\nBleib knapp.\n")
        with patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "ROOT", repo):
            plan = setup.make_plan(self.vault, self.home, "codex", [], [], [])
            staged = setup.stage(plan, self.root / "brain-stage")
            setup.apply(Path(staged["plan"]), staged["sha256"])
        text = (self.vault / "AGENTS.md").read_text()
        self.assertTrue(text.startswith("<!-- BEGIN AGENTIC OS CODEX ADDON -->"))
        self.assertIn("# Meine eigenen Regeln\nBleib knapp.\n", text)
        with patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "ROOT", repo):
            again = setup.make_plan(self.vault, self.home, "codex", [], [], [])
        self.assertEqual(again["changes"], [])
        setup.rollback(Path(staged["plan"]), staged["sha256"])
        self.assertEqual((self.vault / "AGENTS.md").read_text(), "# Meine eigenen Regeln\nBleib knapp.\n")

    def test_discover_lists_vaults_from_obsidian_json(self):
        cfg = self.home / "Library/Application Support/obsidian"
        cfg.mkdir(parents=True)
        other = self.home / "Other"
        other.mkdir()
        (self.vault / ".obsidian/plugins/agentic-os").mkdir(parents=True)
        (self.vault / ".obsidian/plugins/agentic-os/manifest.json").write_text("{}")
        cfg.joinpath("obsidian.json").write_text(json.dumps({"vaults": {"a": {"path": str(self.vault), "open": True}, "b": {"path": str(other)}, "c": {"path": str(self.home / "gone")}}}))
        with patch.object(setup.shutil, "which", return_value=None):
            found = setup.discover(self.home)
        self.assertTrue(found["obsidian_config_found"])
        by_path = {v["path"]: v for v in found["vaults"]}
        self.assertTrue(by_path[str(self.vault)]["agentic_os"])
        self.assertFalse(by_path[str(other)]["agentic_os"])
        self.assertFalse(by_path[str(self.home / "gone")]["exists"])
        self.assertIsNone(found["codex_version"])

    def test_inventory_lists_mcp_names_without_secrets(self):
        (self.home / ".claude.json").write_text(json.dumps({"mcpServers": {"notion": {"url": "https://mcp.notion.com/mcp"}, "secretish": {"command": "x", "env": {"TOKEN": "abc"}}}}))
        (self.vault / ".mcp.json").write_text(json.dumps({"mcpServers": {"linear": {"url": "https://mcp.linear.app/mcp"}}}))
        with patch.object(setup.shutil, "which", return_value=None):
            info = setup.inventory(self.vault, self.home)
        self.assertEqual(info["mcps"], ["linear", "notion", "secretish"])
        self.assertNotIn("abc", json.dumps(info))

    def test_renamed_config_dir_is_detected(self):
        base = self.vault / ".myconfig/plugins/agentic-os"
        base.mkdir(parents=True)
        (base / "manifest.json").write_text("{}")
        self.assertEqual(setup.config_dir(self.vault), ".myconfig")

    def test_stage_private_and_cannot_overwrite(self):
        p = self.plan([])
        self.assertEqual(Path(p["plan"]).stat().st_mode & 0o777, 0o700)
        with self.assertRaisesRegex(setup.SetupError, "new staging directory"):
            self.plan([])

    def test_interrupted_apply_can_rollback(self):
        p = self.plan([self.change(self.target("first"), b"a"), self.change(self.target("second"), b"b")])
        original = setup.atomic_write
        def injected(path, content, mode=0o600):
            if path == self.target("second"):
                raise OSError("simulated interruption")
            return original(path, content, mode)
        with patch.object(setup, "atomic_write", side_effect=injected):
            with self.assertRaises(OSError):
                setup.apply(Path(p["plan"]), p["sha256"])
        self.assertTrue(self.target("first").exists())
        setup.rollback(Path(p["plan"]), p["sha256"])
        self.assertFalse(self.target("first").exists())

    def test_companion_user_modification_blocks_update(self):
        repo = self.root / "bundle"
        build = repo / "host/build"
        build.mkdir(parents=True)
        (build / "manifest.json").write_text(json.dumps({"id": setup.PLUGIN_ID}))
        (build / "main.js").write_bytes(b"new")
        existing = self.vault / ".obsidian/plugins" / setup.PLUGIN_ID
        existing.mkdir(parents=True)
        (existing / "main.js").write_bytes(b"member customization")
        with patch.object(setup, "ROOT", repo):
            with self.assertRaisesRegex(setup.SetupError, "member changes"):
                setup.host_changes(self.vault)

    def test_companion_install_does_not_touch_base_or_data(self):
        repo = self.root / "bundle"
        build = repo / "host/build"
        build.mkdir(parents=True)
        (build / "manifest.json").write_text(json.dumps({"id": setup.PLUGIN_ID}))
        (build / "main.js").write_bytes(b"portable build")
        base = self.vault / ".obsidian/plugins/agentic-os"
        base.mkdir(parents=True)
        (base / "main.js").write_bytes(b"member fork")
        companion = base.parent / setup.PLUGIN_ID
        companion.mkdir()
        (companion / "data.json").write_bytes(b'{"member":"settings"}')
        with patch.object(setup, "ROOT", repo):
            changes = setup.host_changes(self.vault)
            p = self.plan([c for c in changes if c["before"] != c["after"]])
            setup.apply(Path(p["plan"]), p["sha256"])
            again = setup.host_changes(self.vault)
            self.assertTrue(all(c["before"] == c["after"] for c in again))
        self.assertEqual((base / "main.js").read_bytes(), b"member fork")
        self.assertEqual((companion / "data.json").read_bytes(), b'{"member":"settings"}')


if __name__ == "__main__":
    unittest.main()
