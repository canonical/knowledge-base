"""Check the live repository and isolated violations of structural conventions."""

import errno
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "tool/kb"

sys.dont_write_bytecode = True
_loader = importlib.machinery.SourceFileLoader("kb", str(KB))
_spec = importlib.util.spec_from_loader("kb", _loader)
kb = importlib.util.module_from_spec(_spec)
sys.modules["kb"] = kb
_loader.exec_module(kb)

HS = "Read the top-level `.kb/agents.md` file before continuing below."
GOOD = {
    "AGENTS.md": f"""# Preface

Root.

{HS}

# Directory

- `sub/` - Nested knowledge files.

# Documents

- `.kb/agents.md` - General rules.
- `.kb/alpha.md` - Alpha page.
- `sub/AGENTS.md` - Sub index.
""",
    ".kb/agents.md": """# Preface

Rules.

Read the top-level `.kb/agents.md` before continuing below.

# Headers

- _Preface_ - Introduction.
""",
    ".kb/alpha.md": f"# Preface\n\nAlpha.\n\n{HS}\n",
    "sub/AGENTS.md": f"""# Preface

Sub.

{HS}

# Documents

- `.kb/beta.md` - Beta page.
""",
    "sub/.kb/beta.md": f"# Preface\n\nBeta.\n\n{HS}\n",
}


def build(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(KB), "lint", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class LintTest(unittest.TestCase):
    def tmp(self, repository: bool = True) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name).resolve()
        if repository:
            subprocess.run(["git", "init", "-q", str(path)], check=True)
        return path

    def chdir(self, path: Path) -> None:
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(path)

    def checks(self, changes: dict[str, str] | None = None) -> set[str]:
        lint = kb.Lint(build(self.tmp(), GOOD | (changes or {})))
        lint.run()
        return {f["check"] for f in lint.findings}

    def test_live_tree_holds(self):
        proc = cli()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_json_mode(self):
        proc = cli("--json")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout), {"findings": [], "exit": 0})

    def test_clean_synthetic_tree(self):
        self.assertEqual(self.checks(), set())

    def test_preface_first(self):
        for body in ["", "\n", "# Alpha\n\ntext\n"]:
            with self.subTest(body=body):
                self.assertIn("preface-first", self.checks({".kb/alpha.md": body}))

    def test_handshake_line(self):
        for body in [
            "# Preface\n",
            "# Preface\n\nAlpha.\n",
            "# Preface\n\n" + HS.replace(" file", "") + "\n",
        ]:
            with self.subTest(body=body):
                self.assertIn("handshake-line", self.checks({".kb/alpha.md": body}))

    def test_allowed_headers(self):
        for path, header in [
            (".kb/alpha.md", "Index"),
            (".kb/alpha.md", "Directory"),
            (".kb/alpha.md", "Headers"),
            ("AGENTS.md", "Headers"),
        ]:
            with self.subTest(path=path, header=header):
                self.assertIn(
                    "allowed-headers",
                    self.checks({path: GOOD[path] + f"\n# {header}\n"}),
                )

    def test_documents_last(self):
        self.assertIn(
            "documents-last",
            self.checks({"sub/AGENTS.md": GOOD["sub/AGENTS.md"] + "\n# Overview\n"}),
        )

    def test_listing_format(self):
        for section in ["Directory", "Documents"]:
            for item in [
                "- `file`: Description.",
                "- `file` - ",
                "- file - Description.",
                "* `file` - Description.",
                "1. `file` - Description.",
            ]:
                with self.subTest(section=section, item=item):
                    body = "# Preface\n\n" + HS + f"\n\n# {section}\n\n{item}\n"
                    self.assertIn(
                        "listing-format", self.checks({"sub/AGENTS.md": body})
                    )

    def test_ordinary_listing_content(self):
        body = GOOD["AGENTS.md"] + "\nExplanation.\n\n```text\n- illustrative item\n```\n"
        self.assertEqual(self.checks({"AGENTS.md": body}), set())

    def test_existing_conventions_remain_valid(self):
        # No new size, uniqueness, indexing, reachability, or path-existence policies.
        self.assertEqual(
            self.checks(
                {
                    "AGENTS.md": GOOD["AGENTS.md"] + "\nprose" * 200,
                    "sub/.kb/alpha.md": GOOD[".kb/alpha.md"],
                    ".kb/unlisted.md": GOOD[".kb/alpha.md"],
                    "sub/AGENTS.md": "# Preface\n\nSub.\n\n"
                    + HS
                    + "\nSee `.kb/missing.md`.\n",
                }
            ),
            set(),
        )

    def test_documents_in_knowledge_page(self):
        self.assertEqual(
            self.checks(
                {
                    ".kb/alpha.md": GOOD[".kb/alpha.md"]
                    + "\n# Documents\n\nRelated material.\n"
                }
            ),
            set(),
        )

    def test_json_findings(self):
        root = build(self.tmp(), {"AGENTS.md": "wrong\n"})
        proc = cli("--root", str(root), "--json")
        payload = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(payload["exit"], 1)
        self.assertEqual(len(payload["findings"]), 1)
        finding = payload["findings"][0]
        self.assertEqual(finding["file"], "AGENTS.md")
        self.assertEqual(finding["check"], "preface-first")
        self.assertTrue(finding["message"])

    def test_tool_error(self):
        for kind in ["empty", "missing", "file"]:
            with self.subTest(kind=kind):
                target = self.tmp()
                if kind == "missing":
                    target = target / "missing"
                elif kind == "file":
                    target = target / "file"
                    target.write_text("text")
                proc = cli("--root", str(target), "--json")
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(json.loads(proc.stdout), {"findings": [], "exit": 2})

    def test_fenced_headings_are_examples(self):
        for fence in ["```", "~~~~"]:
            with self.subTest(fence=fence):
                body = (
                    GOOD["AGENTS.md"]
                    + f"\n{fence}markdown\n# Index\n- invalid example\n{fence}\n"
                )
                self.assertEqual(self.checks({"AGENTS.md": body}), set())

    def test_repeat_runs_discard_previous_results(self):
        root = build(self.tmp(), GOOD)
        lint = kb.Lint(root)
        page = root / ".kb/alpha.md"
        page.write_text("wrong", encoding="utf-8")
        self.assertEqual(lint.run(), 1)
        page.write_text(GOOD[".kb/alpha.md"], encoding="utf-8")
        self.assertEqual(lint.run(), 0)
        self.assertEqual(lint.findings, [])
        self.assertEqual(len(lint.documents), len(GOOD))
        self.assertEqual(lint.run(), 0)
        self.assertEqual(len(lint.documents), len(GOOD))

    def test_relative_root(self):
        root = build(self.tmp(), GOOD)
        self.chdir(root.parent)
        lint = kb.Lint(Path(root.name))
        self.assertEqual(lint.root, root)
        self.assertEqual(lint.run(), 0)

    def test_each_document_is_read_once(self):
        root = build(self.tmp(), GOOD)
        original_read = Path.read_text
        reads = []

        def read_text(path, *args, **kwargs):
            reads.append(path.relative_to(root).as_posix())
            return original_read(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", read_text):
            self.assertEqual(kb.Lint(root).run(), 0)
        self.assertEqual(sorted(reads), sorted(GOOD))

    def test_read_error_does_not_hide_other_findings(self):
        root = build(self.tmp(), GOOD | {"AGENTS.md": "invalid"})
        unreadable = root / ".kb/alpha.md"
        original_read = Path.read_text

        def read_text(path, *args, **kwargs):
            if path == unreadable:
                raise PermissionError(errno.EACCES, "Permission denied", str(path))
            return original_read(path, *args, **kwargs)

        lint = kb.Lint(root)
        with mock.patch.object(Path, "read_text", read_text):
            self.assertEqual(lint.run(), 2)
        self.assertEqual(
            {(finding["file"], finding["check"]) for finding in lint.findings},
            {(".kb/alpha.md", "tool-error"), ("AGENTS.md", "preface-first")},
        )

    def test_root_inspection_error(self):
        root = self.tmp()

        def is_dir(path):
            raise PermissionError(errno.EACCES, "Permission denied", str(path))

        lint = kb.Lint(root)
        with mock.patch.object(Path, "is_dir", is_dir):
            self.assertEqual(lint.run(), 2)
        self.assertEqual(len(lint.findings), 1)
        self.assertEqual(lint.findings[0]["file"], ".")
        self.assertEqual(lint.findings[0]["check"], "tool-error")

    def test_invalid_utf8_cli(self):
        for json_mode in [False, True]:
            with self.subTest(json_mode=json_mode):
                root = build(self.tmp(), GOOD)
                (root / ".kb/alpha.md").write_bytes(b"\xff")
                arguments = ["--root", str(root)]
                if json_mode:
                    arguments.append("--json")
                result = cli(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)
                if json_mode:
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["exit"], 2)
                    self.assertEqual(payload["findings"][0]["file"], ".kb/alpha.md")
                    self.assertEqual(payload["findings"][0]["check"], "tool-error")
                    self.assertEqual(result.stderr, "")
                else:
                    self.assertIn(".kb/alpha.md: [tool-error]", result.stdout)
                    self.assertIn("tool error", result.stderr)

    def test_git_ignored_files_are_skipped(self):
        root = build(
            self.tmp(),
            GOOD
            | {
                ".gitignore": "vendor/\n.kb/draft.md\n",
                "vendor/pkg/AGENTS.md": "invalid",
                ".kb/draft.md": "invalid",
            },
        )
        lint = kb.Lint(root)
        self.assertEqual(lint.run(), 0)
        self.assertEqual(len(lint.documents), len(GOOD))

    def test_tracked_and_untracked_files_are_checked(self):
        root = build(self.tmp(), GOOD | {"new/AGENTS.md": "invalid"})
        subprocess.run(["git", "-C", str(root), "add", "AGENTS.md"], check=True)
        lint = kb.Lint(root)
        self.assertEqual(lint.run(), 1)
        self.assertEqual(len(lint.documents), len(GOOD) + 1)
        self.assertEqual(
            [finding["file"] for finding in lint.findings], ["new/AGENTS.md"]
        )

    def test_deleted_tracked_file_is_skipped(self):
        root = build(self.tmp(), GOOD | {".kb/gone.md": "invalid"})
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        (root / ".kb/gone.md").unlink()
        self.assertEqual(kb.Lint(root).run(), 0)

    def test_subdirectory_root_keeps_repository_rules(self):
        root = build(self.tmp(), GOOD)
        lint = kb.Lint(root / ".kb")
        self.assertEqual(lint.run(), 0)
        self.assertEqual(len(lint.documents), 2)

    def test_outside_git_repository(self):
        root = build(self.tmp(repository=False), GOOD)
        lint = kb.Lint(root)
        self.assertEqual(lint.run(), 2)
        self.assertEqual(
            [(finding["file"], finding["check"]) for finding in lint.findings],
            [(".", "tool-error")],
        )
        self.assertIn("not inside a git repository", lint.findings[0]["message"])

    def test_deterministic_findings(self):
        files = {"z/.kb/page.md": "invalid", "a/AGENTS.md": "invalid"}
        root = build(self.tmp(), files)
        lint = kb.Lint(root)
        self.assertEqual(lint.run(), 1)
        first = lint.findings.copy()
        for name in files:
            (root / name).unlink()
        build(root, dict(reversed(list(files.items()))))
        self.assertEqual(lint.run(), 1)
        self.assertEqual(lint.findings, first)

    def test_heading_variants_are_checked(self):
        for heading in [" # Index", "   # Index ###", "# Index\t###"]:
            with self.subTest(heading=heading):
                self.assertIn(
                    "allowed-headers",
                    self.checks({".kb/alpha.md": GOOD[".kb/alpha.md"] + f"\n{heading}\n"}),
                )

    def test_valid_heading_variants(self):
        body = GOOD[".kb/alpha.md"] + "\n   # Overview ###\n\nText.\n"
        self.assertEqual(self.checks({".kb/alpha.md": body}), set())

    def test_repeated_documents_cannot_hide_later_sections(self):
        body = GOOD["AGENTS.md"] + "\n# Overview\n\nText.\n\n# Documents\n"
        self.assertIn("documents-last", self.checks({"AGENTS.md": body}))

    def test_fence_closes_before_real_heading(self):
        for opener, closer in [
            ("````python", "`````"),
            ("~~~text", "~~~~"),
            ("   ```", " ```"),
        ]:
            with self.subTest(opener=opener, closer=closer):
                body = GOOD[".kb/alpha.md"] + f"\n{opener}\n# Example\n{closer}\n# Index\n"
                self.assertEqual(
                    self.checks({".kb/alpha.md": body}), {"allowed-headers"}
                )

    def test_false_fence_closer_keeps_examples_hidden(self):
        for false_closer in ["~~~", "``", "``` text"]:
            with self.subTest(false_closer=false_closer):
                body = GOOD["AGENTS.md"] + f"\n```\n{false_closer}\n# Example\n```\n"
                self.assertEqual(self.checks({"AGENTS.md": body}), set())

    def test_invalid_backtick_opener_does_not_hide_heading(self):
        body = GOOD[".kb/alpha.md"] + "\n# Overview\n\n```python`invalid\n# Index\n"
        self.assertEqual(self.checks({".kb/alpha.md": body}), {"allowed-headers"})

    def test_empty_listing_bullet(self):
        for bullet in ["-", "*", "+", "1.", "2)"]:
            with self.subTest(bullet=bullet):
                self.assertIn(
                    "listing-format",
                    self.checks({"AGENTS.md": GOOD["AGENTS.md"] + f"\n{bullet}\n"}),
                )

    def test_nested_listing_explanation_is_ignored(self):
        body = GOOD["AGENTS.md"] + "  - explanatory detail\n"
        self.assertEqual(self.checks({"AGENTS.md": body}), set())


if __name__ == "__main__":
    unittest.main()
