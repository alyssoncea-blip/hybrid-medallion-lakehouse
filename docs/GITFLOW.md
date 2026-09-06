# GitFlow Branching Strategy

This project follows a simplified **GitFlow** workflow adapted for continuous delivery.

## Branch Structure

```text
main ────────────────────────────────────────────▶ (production releases)
  │
  ├── develop ──────────────────────────────────▶ (integration branch)
  │      │
  │      ├── feature/auth-module
  │      ├── fix/login-bug
  │      └── chore/update-deps
  │
  ├── release/v0.3.0 ───────────────────────────▶ (release preparation)
  │
  └── hotfix/critical-security-fix ─────────────▶ (emergency fixes)
```

## Branch Rules

All branches are protected via **GitHub Rulesets**:

| Branch Pattern | Ruleset | Required Checks |
|----------------|---------|-----------------|
| `main` | `main-branch-protection` | markdown-lint, structure-validate, terraform, terraform-test, dbt-build-local |
| `develop` | `develop-branch-protection` | Same 5 core checks |
| `release/*` | `release-branches-protection` | Same 5 core checks |

All rulesets enforce:

- **Active enforcement** — rules cannot be bypassed
- **Required status checks** — 5 core CI jobs must pass
- **Strict policy** — branches must be up to date before merge

## Workflow

### 1. Feature Development

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/my-new-feature

# Work, commit, push
git push origin feature/my-new-feature

# Open PR against develop
gh pr create --base develop --title "feat: my new feature"
```

**Requirements:** PR must pass all 5 core CI checks before merge.

### 2. Release Preparation

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v0.3.0

# Version bump, changelog, final QA
git push origin release/v0.3.0

# Open PR against main
gh pr create --base main --title "release: v0.3.0"
```

**Requirements:** PR must pass all 5 core CI checks before merge.

### 3. Release

```bash
# Merge release/* → main (via PR)
# Tag is created from main after merge
git checkout main
git pull origin main
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0

# Back-merge to develop
git checkout develop
git merge main
git push origin develop
```

### 4. Hotfix (Emergency)

```bash
# Create from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix

# Fix, test, push
git push origin hotfix/critical-fix

# PRs to both main AND develop
gh pr create --base main --title "hotfix: critical fix"
gh pr create --base develop --title "hotfix: critical fix"
```

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on:

- **Push to `main`, `develop`, `release/*`** — Full CI pipeline
- **Pull Requests to `main`, `develop`, `release/*`** — Full CI pipeline

### Required Checks (Core 5)

| Job | Description |
|-----|-------------|
| `markdown-lint` | markdownlint on all `.md` |
| `structure-validate` | Repo structure validation |
| `terraform` | Terraform fmt/validate (4 envs) |
| `terraform-test` | Terraform unit tests |
| `dbt-build-local` | dbt build + tests on DuckDB |

### Optional Checks (continue-on-error)

| Job | Description |
|-----|-------------|
| `mermaid-render` | Mermaid diagram validation |
| `python-lint` | ruff + mypy on Python code |

## Versioning

Follows **Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR** — Breaking changes, architecture shifts
- **MINOR** — New features, backward compatible
- **PATCH** — Bug fixes, backward compatible

## Release Automation

After merging `release/*` → `main`:

1. Create annotated tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
2. Push tag: `git push origin vX.Y.Z`
3. GitHub Actions creates Release (if configured)
4. Back-merge `main` → `develop`

## Branch Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<scope>` | `feat/user-auth` |
| Fix | `fix/<scope>` | `fix/login-redirect` |
| Chore | `chore/<scope>` | `chore/update-deps` |
| Docs | `docs/<scope>` | `docs/api-reference` |
| Release | `release/vX.Y.Z` | `release/v0.3.0` |
| Hotfix | `hotfix/<description>` | `hotfix/security-patch` |

## Commit Messages

Follow **Conventional Commits**:

```text
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`

Example:

```text
feat(airflow): add dbt orchestration DAG

Add DAG for dbt pipeline orchestration with Airflow.
Includes tasks for deps, build, test, docs, freshness.

Closes #42
```

## Enforcement

Rules are enforced at the **GitHub platform level** via Rulesets:

- Direct pushes to protected branches are **blocked**
- PRs must pass all required status checks
- Rulesets cannot be bypassed by regular users
- Admin bypass requires explicit configuration

View rulesets: <https://github.com/alyssoncea-blip/hybrid-medallion-lakehouse/settings/rules>
