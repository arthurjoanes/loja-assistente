#Requires -Version 7.0
param([ValidateSet('setup','start','seed','test','eval','logs','stop','status','demo','check-frontend','e2e')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $projectPath 'compose.yaml'
function Invoke-Compose {
    & docker compose --project-directory $projectPath --file $composePath @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose falhou com código $LASTEXITCODE." }
}
Push-Location -LiteralPath $projectPath
try {
    switch ($Action) {
        'setup' {
            if (!(Test-Path -LiteralPath (Join-Path $projectPath '.env'))) {
                $bytes = New-Object byte[] 32
                [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
                $sessionSecret = [Convert]::ToHexString($bytes).ToLowerInvariant()
                [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
                $databasePassword = [Convert]::ToHexString($bytes).ToLowerInvariant()
                $content = [IO.File]::ReadAllText((Join-Path $projectPath '.env.example'))
                $content = $content.Replace('replace-with-random-project-only-secret', $sessionSecret).Replace('local-demo-only-change-for-shared-environments', $databasePassword)
                [IO.File]::WriteAllText((Join-Path $projectPath '.env'), $content)
            }
            # Separate builds avoid a Buildx/Windows bug with Unicode paths and multiple targets.
            Invoke-Compose build backend
            Invoke-Compose build frontend
            Invoke-Compose up -d --wait db
            Invoke-Compose run --rm backend alembic upgrade head
            Invoke-Compose run --rm backend python -m loja_assistente.seed
        }
        'start' { Invoke-Compose up -d --wait }
        'seed' { Invoke-Compose run --rm backend python -m loja_assistente.seed }
        'test' { Invoke-Compose --profile test run --rm test }
        'eval' { Invoke-Compose --profile test run --rm test python -m evals.runner --output-dir /app/evals/reports/local }
        'check-frontend' {
            Invoke-Compose --profile test build frontend-check
            Invoke-Compose --profile test run --rm frontend-check
        }
        'e2e' {
            $composePath = Join-Path $projectPath 'compose.e2e.yaml'
            try {
                Invoke-Compose down --volumes
                Invoke-Compose build backend
                Invoke-Compose build frontend
                Invoke-Compose build e2e
                Invoke-Compose up --abort-on-container-exit --exit-code-from e2e
            } finally { Invoke-Compose down --volumes }
        }
        'logs' { Invoke-Compose logs --tail 100 -f backend frontend }
        'stop' { Invoke-Compose --profile test down }
        'status' { Invoke-Compose --profile test ps }
        'demo' {
            Write-Output 'Interface: http://localhost:3102 | API: http://localhost:8102/docs'
            Write-Output 'Contas: gerente.a@demo.local, supervisor.a@demo.local, gerente.b@demo.local'
            Write-Output 'Senha fictícia: LojaDemo!2026 | roteiro: docs/demo.md'
        }
    }
} finally { Pop-Location }
