# make-stage-commits.ps1
# Builds the per-stage git history for auth-api (7 commits, one per assignment stage).
# Run it ONCE from anywhere:  powershell -ExecutionPolicy Bypass -File "D:\Flyrank\Week4\Build 2\make-stage-commits.ps1"
# .env is git-ignored and is never touched by this script.

$ErrorActionPreference = "Stop"

$repo   = "D:\Flyrank\Week4\Build 2\auth-api"
$stages = "D:\Flyrank\Week4\Build 2\stage-history"
$coauth = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

Set-Location $repo
git init | Out-Null

if (-not (git config user.name)) {
    Write-Host 'No git identity. Run first:  git config --global user.name "Your Name"'
    exit 1
}
if (-not (git config user.email)) {
    Write-Host 'No git email. Run first:  git config --global user.email "you@example.com"'
    exit 1
}

function Commit-Stage([string]$msg, [string[]]$files) {
    git add -- $files
    if ($LASTEXITCODE -ne 0) { exit 1 }
    git commit -m $msg -m $coauth
    if ($LASTEXITCODE -ne 0) { exit 1 }
    Write-Host ">> committed: $msg"
}

# Stage 0 - setup (main.py is temporarily the stage-1 version so it is NOT added yet)
Copy-Item "$stages\main-stage1.py" "app\main.py" -Force
Commit-Stage "Stage 0: setup server and supabase client" @(
    ".gitignore", ".env.example", "requirements.txt",
    "app/__init__.py", "app/config.py", "app/supabase_client.py"
)

# Stage 1 - signup and login
Commit-Stage "Stage 1: signup and login routes working" @(
    "app/schemas.py", "app/errors.py", "app/main.py"
)

# Stage 2 - public route + unverified protected route
Copy-Item "$stages\main-stage2.py" "app\main.py" -Force
Commit-Stage "Stage 2: public route and unverified protected route" @("app/main.py")

# Stage 3 - token verification
Copy-Item "$stages\main-stage3.py" "app\main.py" -Force
Commit-Stage "Stage 3: profile route token verification" @("app/main.py")

# Stage 4 - reusable dependency + dashboard + logout
Copy-Item "$stages\main-stage4.py" "app\main.py" -Force
Commit-Stage "Stage 4: auth middleware and logout endpoint" @(
    "app/security.py", "app/main.py"
)

# Stage 5 - Swagger polish + root route (final version of the code)
Copy-Item "$stages\main-stage5.py" "app\main.py" -Force
Commit-Stage "Stage 5: Swagger UI documentation with bearer auth" @("app/main.py")

# Stage 6 - README
Commit-Stage "Stage 6: publish to GitHub and write README" @("README.md")

git branch -M main

Write-Host ""
Write-Host "=== History ==="
git log --oneline
Write-Host ""
Write-Host "Total commits: $(git rev-list --count HEAD)"
Write-Host "Tracked .env (MUST be empty): [$(git ls-files -- .env)]"
Write-Host ""
Write-Host "Done. Next: create a public repo on GitHub, then:"
Write-Host '  git remote add origin https://github.com/<your-username>/auth-api.git'
Write-Host "  git push -u origin main"