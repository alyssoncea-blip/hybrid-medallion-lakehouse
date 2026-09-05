# Conventions

This document describes the conventions enforced across the Hybrid Medallion Lakehouse repository.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/) with these types:

- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `refactor` — code change that neither fixes a bug nor adds a feature
- `perf` — performance improvement
- `test` — adding or fixing tests
- `build` — build system or external dependencies
- `ci` — CI configuration
- `chore` — other (tooling, formatting)
- `revert` — revert a previous commit

Examples:

- `feat(dbt): add silver customers conformed model`
- `fix(terraform): correct role grant for ingest role`
- `docs(charter): update budget estimate`
- `ci(github-actions): add terraform plan workflow`

## Branch naming

- `feat/<scope>` — new feature
- `fix/<scope>` — bug fix
- `chore/<scope>` — tooling
- `docs/<scope>` — documentation
- `release/<version>` — release prep

## Pull request rules

- Title must be a Conventional Commit (`feat:`, `fix:`, etc.)
- Description must use the template in `.github/PULL_REQUEST_TEMPLATE.md`
- Link the related issue with `Closes #N` or `Refs #N`
- At least 1 reviewer approval required
- All CI checks must pass before merge

## Squash merge policy

- PRs are squash-merged into `main` or `develop`
- Source branches are deleted after merge

## Code style

- Terraform: `terraform fmt` clean
- Markdown: `markdownlint` clean (see `.markdownlint.jsonc`)
- SQL/dbt: dbt parser clean (no deprecation warnings)
- Python: `ruff` clean
