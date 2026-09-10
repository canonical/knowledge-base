"""Check the live repository and isolated violations of structural conventions."""

import errno
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kb_lint  # noqa: E402

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


def build(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def checks(tmp_path: Path, changes: dict[str, str] | None = None) -> set[str]:
    lint = kb_lint.Lint(build(tmp_path, GOOD | (changes or {})))
    lint.run()
    return {f["check"] for f in lint.findings}


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools/kb_lint.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_live_tree_holds():
    proc = cli()
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_json_mode():
    proc = cli("--json")
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {"findings": [], "exit": 0}


def test_clean_synthetic_tree(tmp_path):
    assert checks(tmp_path) == set()


@pytest.mark.parametrize("body", ["", "\n", "# Alpha\n\ntext\n"])
def test_preface_first(tmp_path, body):
    assert "preface-first" in checks(tmp_path, {".kb/alpha.md": body})


@pytest.mark.parametrize(
    "body",
    [
        "# Preface\n",
        "# Preface\n\nAlpha.\n",
        "# Preface\n\n" + HS.replace(" file", "") + "\n",
    ],
)
def test_handshake_line(tmp_path, body):
    assert "handshake-line" in checks(tmp_path, {".kb/alpha.md": body})


@pytest.mark.parametrize(
    "path,header",
    [
        (".kb/alpha.md", "Index"),
        (".kb/alpha.md", "Directory"),
        (".kb/alpha.md", "Headers"),
        ("AGENTS.md", "Headers"),
    ],
)
def test_allowed_headers(tmp_path, path, header):
    assert "allowed-headers" in checks(tmp_path, {path: GOOD[path] + f"\n# {header}\n"})


def test_documents_last(tmp_path):
    assert "documents-last" in checks(
        tmp_path, {"sub/AGENTS.md": GOOD["sub/AGENTS.md"] + "\n# Overview\n"}
    )


@pytest.mark.parametrize("section", ["Directory", "Documents"])
@pytest.mark.parametrize(
    "item",
    [
        "- `file`: Description.",
        "- `file` - ",
        "- file - Description.",
        "* `file` - Description.",
        "1. `file` - Description.",
    ],
)
def test_listing_format(tmp_path, section, item):
    body = "# Preface\n\n" + HS + f"\n\n# {section}\n\n{item}\n"
    assert "listing-format" in checks(tmp_path, {"sub/AGENTS.md": body})


def test_ordinary_listing_content(tmp_path):
    body = GOOD["AGENTS.md"] + "\nExplanation.\n\n```text\n- illustrative item\n```\n"
    assert checks(tmp_path, {"AGENTS.md": body}) == set()


def test_existing_conventions_remain_valid(tmp_path):
    # No new size, uniqueness, indexing, reachability, or path-existence policies.
    assert (
        checks(
            tmp_path,
            {
                "AGENTS.md": GOOD["AGENTS.md"] + "\nprose" * 200,
                "sub/.kb/alpha.md": GOOD[".kb/alpha.md"],
                ".kb/unlisted.md": GOOD[".kb/alpha.md"],
                "sub/AGENTS.md": "# Preface\n\nSub.\n\n"
                + HS
                + "\nSee `.kb/missing.md`.\n",
            },
        )
        == set()
    )


def test_documents_in_knowledge_page(tmp_path):
    assert (
        checks(
            tmp_path,
            {
                ".kb/alpha.md": GOOD[".kb/alpha.md"]
                + "\n# Documents\n\nRelated material.\n"
            },
        )
        == set()
    )


def test_json_findings(tmp_path):
    build(tmp_path, {"AGENTS.md": "wrong\n"})
    proc = cli("--root", str(tmp_path), "--json")
    payload = json.loads(proc.stdout)
    assert proc.returncode == payload["exit"] == 1
    assert len(payload["findings"]) == 1
    finding = payload["findings"][0]
    assert finding["file"] == "AGENTS.md"
    assert finding["check"] == "preface-first"
    assert finding["message"]


@pytest.mark.parametrize("kind", ["empty", "missing", "file"])
def test_tool_error(tmp_path, kind):
    target = tmp_path
    if kind == "missing":
        target = tmp_path / "missing"
    elif kind == "file":
        target = tmp_path / "file"
        target.write_text("text")
    proc = cli("--root", str(target), "--json")
    assert proc.returncode == 2
    assert json.loads(proc.stdout) == {"findings": [], "exit": 2}


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_fenced_headings_are_examples(tmp_path, fence):
    body = (
        GOOD["AGENTS.md"] + f"\n{fence}markdown\n# Index\n- invalid example\n{fence}\n"
    )
    assert checks(tmp_path, {"AGENTS.md": body}) == set()


def test_repeat_runs_discard_previous_results(tmp_path):
    build(tmp_path, GOOD)
    lint = kb_lint.Lint(tmp_path)
    page = tmp_path / ".kb/alpha.md"
    page.write_text("wrong", encoding="utf-8")
    assert lint.run() == 1
    page.write_text(GOOD[".kb/alpha.md"], encoding="utf-8")
    assert lint.run() == 0
    assert lint.findings == []
    assert len(lint.documents) == len(GOOD)
    assert lint.run() == 0
    assert len(lint.documents) == len(GOOD)


def test_relative_root(tmp_path, monkeypatch):
    build(tmp_path, GOOD)
    monkeypatch.chdir(tmp_path.parent)
    lint = kb_lint.Lint(Path(tmp_path.name))
    assert lint.root == tmp_path
    assert lint.run() == 0


def test_each_document_is_read_once(tmp_path, monkeypatch):
    build(tmp_path, GOOD)
    original_read = Path.read_text
    reads = []

    def read_text(path, *args, **kwargs):
        reads.append(path.relative_to(tmp_path).as_posix())
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    assert kb_lint.Lint(tmp_path).run() == 0
    assert sorted(reads) == sorted(GOOD)


def test_ignored_directories_are_not_entered(tmp_path, monkeypatch):
    build(tmp_path, GOOD)
    for directory in kb_lint.IGNORED_DIRECTORIES:
        build(tmp_path, {f"{directory}/AGENTS.md": "invalid"})
    original_scandir = kb_lint.os.scandir
    visited = []

    def scandir(path):
        visited.append(Path(path))
        return original_scandir(path)

    monkeypatch.setattr(kb_lint.os, "scandir", scandir)
    assert kb_lint.Lint(tmp_path).run() == 0
    assert all(path.name not in kb_lint.IGNORED_DIRECTORIES for path in visited)


def test_read_error_does_not_hide_other_findings(tmp_path, monkeypatch):
    build(tmp_path, GOOD | {"AGENTS.md": "invalid"})
    unreadable = tmp_path / ".kb/alpha.md"
    original_read = Path.read_text

    def read_text(path, *args, **kwargs):
        if path == unreadable:
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    lint = kb_lint.Lint(tmp_path)
    assert lint.run() == 2
    assert {(finding["file"], finding["check"]) for finding in lint.findings} == {
        (".kb/alpha.md", "tool-error"),
        ("AGENTS.md", "preface-first"),
    }


def test_directory_error_is_reported(tmp_path, monkeypatch):
    build(tmp_path, GOOD)
    original_scandir = kb_lint.os.scandir

    def scandir(path):
        if Path(path) == tmp_path / "sub":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original_scandir(path)

    monkeypatch.setattr(kb_lint.os, "scandir", scandir)
    lint = kb_lint.Lint(tmp_path)
    assert lint.run() == 2
    assert len(lint.findings) == 1
    assert lint.findings[0]["file"] == "sub"
    assert lint.findings[0]["check"] == "tool-error"


def test_root_inspection_error(tmp_path, monkeypatch):
    def is_dir(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(Path, "is_dir", is_dir)
    lint = kb_lint.Lint(tmp_path)
    assert lint.run() == 2
    assert len(lint.findings) == 1
    assert lint.findings[0]["file"] == "."
    assert lint.findings[0]["check"] == "tool-error"


@pytest.mark.parametrize("json_mode", [False, True])
def test_invalid_utf8_cli(tmp_path, json_mode):
    build(tmp_path, GOOD)
    (tmp_path / ".kb/alpha.md").write_bytes(b"\xff")
    arguments = ["--root", str(tmp_path)]
    if json_mode:
        arguments.append("--json")
    result = cli(*arguments)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    if json_mode:
        payload = json.loads(result.stdout)
        assert payload["exit"] == 2
        assert payload["findings"][0]["file"] == ".kb/alpha.md"
        assert payload["findings"][0]["check"] == "tool-error"
        assert result.stderr == ""
    else:
        assert ".kb/alpha.md: [tool-error]" in result.stdout
        assert "tool error" in result.stderr


def test_symlink_policy(tmp_path):
    build(tmp_path, GOOD)
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
    external = tmp_path.parent / f"{tmp_path.name}-external"
    build(external, {"AGENTS.md": "invalid"})
    (tmp_path / "linked-directory").symlink_to(external, target_is_directory=True)
    (tmp_path / ".kb/linked.md").symlink_to(tmp_path / ".kb/alpha.md")
    lint = kb_lint.Lint(tmp_path)
    assert lint.run() == 0
    assert len(lint.documents) == len(GOOD) + 1


def test_deterministic_findings(tmp_path):
    files = {"z/.kb/page.md": "invalid", "a/AGENTS.md": "invalid"}
    build(tmp_path, files)
    lint = kb_lint.Lint(tmp_path)
    assert lint.run() == 1
    first = lint.findings.copy()
    for name in files:
        (tmp_path / name).unlink()
    build(tmp_path, dict(reversed(list(files.items()))))
    assert lint.run() == 1
    assert lint.findings == first


@pytest.mark.parametrize("heading", [" # Index", "   # Index ###", "# Index\t###"])
def test_heading_variants_are_checked(tmp_path, heading):
    assert "allowed-headers" in checks(
        tmp_path, {".kb/alpha.md": GOOD[".kb/alpha.md"] + f"\n{heading}\n"}
    )


def test_valid_heading_variants(tmp_path):
    body = GOOD[".kb/alpha.md"] + "\n   # Overview ###\n\nText.\n"
    assert checks(tmp_path, {".kb/alpha.md": body}) == set()


def test_repeated_documents_cannot_hide_later_sections(tmp_path):
    body = GOOD["AGENTS.md"] + "\n# Overview\n\nText.\n\n# Documents\n"
    assert "documents-last" in checks(tmp_path, {"AGENTS.md": body})


@pytest.mark.parametrize(
    "opener,closer",
    [
        ("````python", "`````"),
        ("~~~text", "~~~~"),
        ("   ```", " ```"),
    ],
)
def test_fence_closes_before_real_heading(tmp_path, opener, closer):
    body = GOOD[".kb/alpha.md"] + f"\n{opener}\n# Example\n{closer}\n# Index\n"
    assert checks(tmp_path, {".kb/alpha.md": body}) == {"allowed-headers"}


@pytest.mark.parametrize("false_closer", ["~~~", "``", "``` text"])
def test_false_fence_closer_keeps_examples_hidden(tmp_path, false_closer):
    body = GOOD["AGENTS.md"] + f"\n```\n{false_closer}\n# Example\n```\n"
    assert checks(tmp_path, {"AGENTS.md": body}) == set()


def test_invalid_backtick_opener_does_not_hide_heading(tmp_path):
    body = GOOD[".kb/alpha.md"] + "\n# Overview\n\n```python`invalid\n# Index\n"
    assert checks(tmp_path, {".kb/alpha.md": body}) == {"allowed-headers"}


@pytest.mark.parametrize("bullet", ["-", "*", "+", "1.", "2)"])
def test_empty_listing_bullet(tmp_path, bullet):
    assert "listing-format" in checks(
        tmp_path, {"AGENTS.md": GOOD["AGENTS.md"] + f"\n{bullet}\n"}
    )


def test_nested_listing_explanation_is_ignored(tmp_path):
    body = GOOD["AGENTS.md"] + "  - explanatory detail\n"
    assert checks(tmp_path, {"AGENTS.md": body}) == set()
