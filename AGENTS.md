# Preface

_[PLACEHOLDER]_
This is the only required section under our AGENTS.md conventions, and it serves to quickly instruct the agent on whether the content inside this file and directory is relevant or not for its current task. Focus on accomplishing this goal while being as terse as possible. The rest of the file will provide the details. Then, always end every Preface section with the following line for cross-linking.
_[/PLACEHOLDER]_

Read the top-level `.kb/agents.md` file before continuing below.


# Overview

_[PLACEHOLDER]_
An optional general project overview. Resist the temptation to document your whole project in this file. Instead, break it down into independent small documents following the .kb/some-topic.md style.
_[/PLACEHOLDER]_


# Important

- Run `tool/kb lint` after editing knowledge files; see `.kb/linting.md` for usage.


# Architecture

_[PLACEHOLDER]_
An optional general project architecture. Resist the temptation to document your whole project in this file. Instead, break it down into independent small documents following the .kb/some-topic.md style.
_[/PLACEHOLDER]_


# Directory

- `tool/` - The `kb` knowledge base helper (`kb lint`) and its tests.
- `sample/` - Non-existent sample entry to illustrate the formatting here.

_[PLACEHOLDER]_
This section holds an optional terse summary for the relevant files and directories living next to this AGENTS.md file. It may also include content under nested subdirectories when these do not have enough content to justify their own AGENTS.md file. Do not include .kb/*.md content here. This section will typically be maintained by the agent itself.
_[/PLACEHOLDER]_


# Documents

- `.kb/agents.md` - General rules for the knowledge base reading and writing.
- `.kb/linting.md` - Checker usage and supported structural checks.

_[PLACEHOLDER]_
This section, generally optional, is used to provide a short summary of what documentation is available under .kb/*.md and also to other immediately nested AGENTS.md. For the top-level directory, this section will always contain at least the reference to the general rules. This section will typically be maintained by the agent itself.
_[/PLACEHOLDER]_
