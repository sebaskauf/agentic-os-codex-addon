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

    def test_windows_can_inspect_but_not_install(self):
        with patch.object(setup.sys, "platform", "win32"), patch.object(setup.shutil, "which", return_value=None):
            self.assertFalse(setup.inventory(self.vault, self.home)["supported_host_install"])
            with self.assertRaisesRegex(setup.SetupError, "macOS-only"):
                setup.make_plan(self.vault, self.home, "codex", [], [], [])

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
