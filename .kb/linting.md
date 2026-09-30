# Preface

This page explains how to check knowledge-base document structure.

Read the top-level `.kb/agents.md` file before continuing below.


# Overview

Run `tool/kb lint` after editing knowledge files. The checker uses only the Python standard library; so do its tests (`python3 -m unittest discover -s tool/tests`).

Pass files or directories to check only those; the default is the whole repository. Each problem prints as `<file>:<line>: <message>`, followed by a summary of what to do next.

Unreadable files are reported on stderr; readable files are still checked. Files are discovered through git, so anything git ignores is skipped; outside a git repository the checker reports a tool error.


# Important

- Checks cover Preface placement, the required handshake, allowed top-level headers, Documents placement, and Directory/Documents listing syntax.
- The root rules page's existing handshake without the word "file" is accepted for compatibility.
- Directory is restricted to `AGENTS.md`; Documents remains accepted in knowledge pages as directed by the existing Directory guidance.
- The checker imposes no line limits, mandatory indexing, or path-existence requirements.
