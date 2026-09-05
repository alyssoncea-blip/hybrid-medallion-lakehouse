# GitHub Repository Setup

After the first push, complete these one-time configurations in the GitHub UI.

## Branch protection rules

Go to **Settings → Branches → Add rule**:

| Field | Value |
|---|---|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ |
| Require approvals | 1 (or 2 for stricter governance) |
| Dismiss stale pull request approvals when new commits are pushed | ✅ |
| Require status checks to pass before merging | ✅ |
| Require branches to be up to date before merging | ✅ |
| Status checks that are required | (after first CI run, select all 7 jobs): |
| | `markdown-lint` |
| | `mermaid-render` |
| | `structure-validate` |
| | `terraform (local)` |
| | `terraform (dev)` |
| | `terraform (stg)` |
| | `terraform (prd)` |
| | `terraform-test` |
| | `dbt-build-local` |
| | `python-lint` |
| | `all-checks-passed` |
| Require linear history | ✅ |
| Include administrators | ✅ (so the same rules apply to you) |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |

## Repository secrets (optional, for Snowflake dbt job)

Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Required | Example |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | yes (for snowflake job) | `acme.sa-east-1` |
| `SNOWFLAKE_USER` | yes | `hybrid_lakehouse_terraform` |
| `SNOWFLAKE_PASSWORD` | yes (or use key-pair / SSO) | (from Snowflake → User → Reset password) |
| `SNOWFLAKE_ROLE` | optional | `DEV_HYBRID_LH_TRANSFORM_ROLE` |
| `SNOWFLAKE_WAREHOUSE` | optional | `DEV_HYBRID_LH_TRANSFORM_WH` |
| `SNOWFLAKE_DATABASE` | optional | `DEV_HYBRID_LH_SILVER` |

**Without these secrets**, the `dbt-build-snowflake` job is automatically skipped and the pipeline still passes (default R$ 0 mode).

## Variables (optional, for Snowflake dbt job)

If using key-pair authentication instead of password:

| Variable | Example |
|---|---|
| `SNOWFLAKE_PRIVATE_KEY` | (paste the private key contents) |
| `SNOWFLAKE_AUTHENTICATOR` | `jwt` |

## Environment protection (recommended for production)

Settings → Environments → New environment → `production`:

- **Required reviewers**: add yourself + 1 other
- **Deployment branches**: only `main`
- **Wait timer**: 5 minutes (gives a window to cancel)

Then update `.github/workflows/ci.yml` to add a `production` job that runs on `release/*` tags with `environment: production`.

## Default branch

Settings → General → Default branch → `main` (it should already be set after the first push).

## Releases

To create a release:

1. Tag a commit: `git tag -a v0.2.0 -m "Release v0.2.0"`
2. Push the tag: `git push origin v0.2.0`
3. Go to **Releases → Draft a new release → Choose tag v0.2.0**
4. Title: `Hybrid Medallion Lakehouse v0.2.0`
5. Description: copy from [`docs/RELEASE-v0.2.0.md`](docs/RELEASE-v0.2.0.md)
6. **Publish release**

GitHub will auto-create a tarball/zip of the source at that tag and generate release notes from PRs.

## GitHub Pages (optional, for hosted docs)

To publish this README and the numbered docs as a website:

1. Settings → Pages → Source: **Deploy from a branch**
2. Branch: `main`, folder: `/` (or create a `docs/` index page)
3. After ~2 minutes, the site is live at `https://alyssoncea-blip.github.io/hybrid-medallion-lakehouse/`

For a richer docs site, consider [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) or [Docusaurus](https://docusaurus.io/) in a follow-up release.

## Issue labels (recommended)

Settings → Labels → create these:

| Label | Color | Purpose |
|---|---|---|
| `bug` | `#d73a4a` | Something isn't working |
| `enhancement` | `#a2eeef` | New feature request |
| `documentation` | `#0075ca` | Improvements to docs |
| `governance` | `#7057ff` | Data governance change |
| `security` | `#b60205` | Security disclosure |
| `good first issue` | `#7057ff` | Easy entry point for new contributors |
| `help wanted` | `#008672` | Need community help |
| `wontfix` | `#ffffff` | Closed without action |

## Topics (for discoverability)

Settings → General → Topics: add

- `data-warehouse`
- `snowflake`
- `dbt`
- `medallion-architecture`
- `data-engineering`
- `data-governance`
- `lgpd`
- `terraform`
- `lakehouse`
- `analytics`
