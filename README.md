
# Overview

This repository defines the Canonical convention to be used in our source code repositories to help agents read and write documentation into a knowledge base inside the source code repository.

The design of this structure has the following key goals:

- **Mechanical** - Agents are the main actors reading and writing the knowledge base.
- **Generic** - Benefits any agentic workflow, no matter the editor or platform.
- **Distilled** - Avoids the use of verbose task or plan logs that pollute the context window.
- **Hierarchical** - Avoids excessive information in a single place that also pollutes the context window.
- **Human** - Information is readily available and reviewable in a friendly format.

# Rules

The document you are reading is an introduction for you the human, not for the agent.

The basic idea is simple: `AGENTS.md` files become simplified indexes into information that is kept up-to-date in more specific files named as `.kb/some-topic.md`. **These subdirectories are located throughout the repository, not just at the top-level,** so that relevant content is close to where it belongs, and so that the hierarchical nature of source code repositories is respected. Agents are then encouraged to read and write those files under the more specific rules that are defined in `.kb/agents.md`.

This approach is in contrast to other techniques, such as persisting plans or logs, which will languish and become out of date due to their historical nature.

# Adoption

To adopt these rules, simply:

1. Copy the `.kb/agents.md` file to the same location in your repository
2. Copy the `AGENTS.md` file to the top-level of your repository and edit it
3. Encourage agents to read and write content into the knowledge base.


Optionally, copy `tool/kb` and run `tool/kb lint` in CI or before committing to check document structure. See `.kb/linting.md` for usage.

# Updating

To update the rules:

1. Overwrite the `.kb/agents.md` file with a new copy from this repository
2. Before committing, ask the agent to verify the changes and apply them to the entire repository.
3. Commit all the changes at once.

# Contact

- Matias Piipari (mz2)
- Gustavo Niemeyer (niemeyer)

# Roadmap

- [x] Define the seed team, meet regularly
- [x] Define knowledge base rules
- [x] Establish the skeleton repository
- [ ] Evaluate the need for harness-specific cross-linking
- [ ] Research and establish skills rules
