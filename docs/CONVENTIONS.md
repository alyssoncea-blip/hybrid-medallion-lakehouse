# Pull Request title and description conventions:
# - Title: Conventional Commit (feat:, fix:, docs:, etc.)
# - Description: use the template in .github/PULL_REQUEST_TEMPLATE.md
# - Link related issue with Closes #N or Refs #N
# - At least 1 reviewer approval required
# - All CI checks must pass before merge

branches:
  - main
  - develop

pull_request:
  branches:
    - main
    - develop
  reviews:
    required: 1
  checks:
    - markdownlint
    - mermaid-render
    - terraform-validate
    - dbt-build
    - python-lint

commit_message:
  max_length: 120
  enforce_conventional: true

merge:
  method: squash
  delete_branch: true
