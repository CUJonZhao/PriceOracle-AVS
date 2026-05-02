param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Upstream,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$UpstreamRoot = (Resolve-Path -LiteralPath $Upstream).Path

if (-not (Test-Path -LiteralPath (Join-Path $UpstreamRoot "aggregator"))) {
    throw "error: $UpstreamRoot does not look like the upstream repo (missing aggregator/)"
}
if (-not (Test-Path -LiteralPath (Join-Path $UpstreamRoot "core\chainio"))) {
    throw "error: $UpstreamRoot does not look like the upstream repo (missing core/chainio/)"
}

$BindingPath = Join-Path $UpstreamRoot "contracts\bindings\IncredibleSquaringTaskManager\binding.go"
if (Test-Path -LiteralPath $BindingPath) {
    $BindingText = Get-Content -LiteralPath $BindingPath -Raw
    if ($BindingText -match "NumberToBeSquared") {
        Write-Warning "$BindingPath still references NumberToBeSquared. M1 bindings must be regenerated before this patch can compile."
    }
}

$Files = @(
    @{ Source = "aggregator.go.proposed"; Destination = "aggregator\aggregator.go" },
    @{ Source = "rpc_server.go.proposed"; Destination = "aggregator\rpc_server.go" },
    @{ Source = "aggregator_test.go.proposed"; Destination = "aggregator\aggregator_test.go" },
    @{ Source = "rpc_server_test.go.proposed"; Destination = "aggregator\rpc_server_test.go" },
    @{ Source = "aggregator_chain_mock.go.proposed"; Destination = "aggregator\mocks\chain.go" },
    @{ Source = "avs_writer.go.proposed"; Destination = "core\chainio\avs_writer.go" },
    @{ Source = "avs_writer_mock.go.proposed"; Destination = "core\chainio\mocks\avs_writer.go" },
    @{ Source = "median.go"; Destination = "aggregator\median.go" },
    @{ Source = "median_test.go"; Destination = "aggregator\median_test.go" },
    @{ Source = "challenger.go.proposed"; Destination = "challenger\challenger.go" },
    @{ Source = "challenger_test.go.proposed"; Destination = "challenger\challenger_test.go" }
)

foreach ($File in $Files) {
    $Source = Join-Path $Here $File.Source
    $Destination = Join-Path $UpstreamRoot $File.Destination
    $Backup = "$Destination.preM3.bak"

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "missing staged file: $Source"
    }

    if ($DryRun) {
        Write-Host "would copy $Source -> $Destination"
        if ((Test-Path -LiteralPath $Destination) -and -not (Test-Path -LiteralPath $Backup)) {
            Write-Host "would backup $Destination -> $Backup"
        }
        continue
    }

    if ((Test-Path -LiteralPath $Destination) -and -not (Test-Path -LiteralPath $Backup)) {
        Copy-Item -LiteralPath $Destination -Destination $Backup
    }

    $DestinationDir = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $DestinationDir)) {
        New-Item -ItemType Directory -Path $DestinationDir | Out-Null
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    Write-Host "copied $($File.Source) -> $($File.Destination)"
}

Write-Host ""
Write-Host "Done. Next steps inside ${UpstreamRoot}:"
Write-Host "  gofmt -w aggregator core/chainio challenger"
Write-Host "  go build ./..."
Write-Host "  go test ./aggregator/... ./challenger/..."
