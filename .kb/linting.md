# Preface

This page explains how to check knowledge-base document structure.

Read the top-level `.kb/agents.md` file before continuing below.


# Overview

Run `python3 tools/kb_lint.py` after editing knowledge files. The checker uses only the Python standard library; run its tests with `python3 -m pytest -q tests/` after installing pytest.

Use `--root ../other` to check another repository or `--json` for structured output (`{"findings": [...], "exit": N}`). Text findings use `<file>: [<check>] <message>`. Exit codes are 0 for success, 1 for findings, and 2 for an invalid root or no knowledge files.

Filesystem and UTF-8 decoding failures produce `tool-error` findings and exit 2, even if readable files also have convention violations. Readable files are still checked. Ignored dependency/cache directories and directory symlinks are not traversed; readable file symlinks are supported.


# Important

- Checks cover Preface placement, the required handshake, allowed top-level headers, Documents placement, and Directory/Documents listing syntax.
- The root rules page's existing handshake without the word "file" is accepted for compatibility.
- Directory is restricted to `AGENTS.md`; Documents remains accepted in knowledge pages as directed by the existing Directory guidance.
- The checker imposes no line limits, mandatory indexing, or path-existence requirements.
