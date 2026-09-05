# Hybrid Medallion Lakehouse — PowerShell entry point
# Mirrors the Makefile targets for Windows users. Use: `./make.ps1 <target>`.

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"

$RepoRoot      = Resolve-Path "$PSScriptRoot\.."
$DocsDir       = $RepoRoot.Path
$TerraformDir  = Join-Path $RepoRoot.Path "src\terraform"
$DbtDir        = Join-Path $RepoRoot.Path "src\dbt"
$ScriptsDir    = Join-Path $RepoRoot.Path "scripts"

function Invoke-Target {
    param([string]$Name)
    Write-Host ">> $Name" -ForegroundColor Cyan
    switch ($Name) {
        "help" {
            Write-Host "Available targets:" -ForegroundColor Yellow
            Get-Content "$PSScriptRoot\targets.txt" | ForEach-Object { Write-Host "  $_" }
        }
        "setup"        { npm install }
        "lint"         { Invoke-Target "lint-md"; Invoke-Target "lint-tf" }
        "lint-md"      { npm run lint:md }
        "lint-md-fix"  { npm run lint:md:fix }
        "lint-tf"      { terraform fmt -check -recursive $TerraformDir }
        "lint-tf-fix"  { terraform fmt -recursive $TerraformDir }
        "validate"     { Invoke-Target "validate-tf"; Invoke-Target "validate-mermaid" }
        "validate-tf" {
            foreach ($env in @("dev","stg","prd")) {
                $envPath = Join-Path $TerraformDir "environments\$env"
                if (Test-Path $envPath) {
                    Push-Location $envPath
                    try { terraform init -backend=false -no-color; terraform validate } finally { Pop-Location }
                }
            }
        }
        "validate-mermaid" { npm run render:mermaid }
        "test"         { Invoke-Target "lint"; Invoke-Target "validate" }
        "test-all"     { Invoke-Target "lint"; Invoke-Target "validate" }
        "dbt-deps"     { Push-Location $DbtDir; try { dbt deps } finally { Pop-Location } }
        "dbt-build"    { Push-Location $DbtDir; try { dbt deps; dbt build --target dev } finally { Pop-Location } }
        "dbt-test"     { Push-Location $DbtDir; try { dbt test } finally { Pop-Location } }
        "clean" {
            Remove-Item node_modules -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item "$DbtDir\dbt_packages","$DbtDir\target","$DbtDir\logs" -Recurse -Force -ErrorAction SilentlyContinue
            Get-ChildItem $TerraformDir -Directory -Recurse -Filter ".terraform" | Remove-Item -Recurse -Force
        }
        "pre-commit"   { pre-commit run --all-files }
        default {
            Write-Host "Unknown target: $Name" -ForegroundColor Red
            Invoke-Target "help"
            exit 1
        }
    }
}

Invoke-Target -Name $Target
