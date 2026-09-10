---
trigger: always_on
---

# Olist Kaggle Project — Project Rules

## Project Context

This is a portfolio Data Engineering project based on the Brazilian E-Commerce Public Dataset by Olist.

For the complete project context, decisions, environment, and current state, refer to:

@../../docs/project_context.md

## General Principles

- Keep the project appropriate for a junior-to-mid-level Data Engineering portfolio.
- Prefer simple, maintainable, explainable solutions over unnecessary complexity.
- Do not introduce technologies only to make the project look more advanced.
- Do not add AI agents, LLM-based processing, or autonomous AI components to the data pipeline unless explicitly requested by the user.
- The user makes the final architectural and technical decisions.
- Before making significant architectural changes, explain the reasoning and trade-offs.
- Do not silently change previously established project decisions.
- Use English language only

## Data

- The source dataset is the Brazilian E-Commerce Public Dataset by Olist from Kaggle.
- Raw data must remain outside version control.
- Never commit raw datasets, API tokens, passwords, credentials, or secrets.
- Do not modify raw source files directly.
- Preserve data lineage and reproducibility whenever data transformations are introduced.

## Code

- Prefer readable and straightforward Python and SQL.
- Avoid unnecessary abstractions.
- Do not create excessive files, classes, functions, or frameworks without a clear reason.
- Keep dependencies to the minimum necessary.
- Follow existing project conventions once they are established.
- When changing existing code, preserve working behavior unless the change explicitly requires otherwise.

## Git

- Do not commit secrets or credentials.
- Do not commit `.venv/`.
- Do not commit raw datasets.
- Do not create commits automatically unless explicitly requested by the user.
- Before recommending a commit, verify that sensitive or generated files are not staged.

## Agent Behavior

- First inspect the relevant existing files before proposing changes.
- Do not assume that a technology or architecture is required merely because it is common in Data Engineering.
- When multiple reasonable approaches exist, briefly explain the relevant trade-offs and recommend the simplest appropriate option.
- Avoid overengineering.
- If a requirement is ambiguous and materially affects the implementation, ask the user before proceeding.
- Do not overwrite or delete files without a clear reason and user approval when the operation could cause data loss.