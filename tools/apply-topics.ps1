# apply-topics.ps1
# Automates setting GitHub topic tags across the Australian accounting tech ecosystem repositories.
# Requires: GitHub CLI (`gh auth status`)

$ErrorActionPreference = "Stop"

$repoTopics = @{
    "ryanduguid/australian-accounting" = @("mcp-server", "model-context-protocol", "australian-taxation", "accounting", "python", "australian-accounting")
    "ryanduguid/Ozzit" = @("excel-lambda", "dynamic-arrays", "financial-modelling", "cash-flow", "gst")
    "ryanduguid/australian-accounting-skills" = @("claude-code", "agent-skills", "public-practice", "australian-accounting")
    "ryanduguid/llm-tax-guardrails" = @("ai-guardrails", "ethics", "apes-110", "tpb", "tax-agents")
    "ryanduguid/au-tax-legislation-corpus" = @("legislation-corpus", "tax-law", "australian-taxation", "python")
    "ryanduguid/accounting-review-pipeline" = @("trial-balance", "close-controls", "financial-reporting", "reconciliation", "python", "monthly-close")
}

Write-Host "Applying repository topic tags across public repositories..." -ForegroundColor Cyan

foreach ($repo in $repoTopics.Keys) {
    $topics = $repoTopics[$repo]
    Write-Host "Updating topics for ${repo}: $($topics -join ', ')" -ForegroundColor Yellow
    $topicArgs = @($topics | ForEach-Object { "--add-topic", $_ })
    gh repo edit $repo @topicArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update topics for ${repo} (GitHub CLI exit $LASTEXITCODE)."
    }
}

Write-Host "All repository topic tags successfully updated." -ForegroundColor Green
