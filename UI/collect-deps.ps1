# collect-deps.ps1
# Collects all npm dependencies (including transitive) from the current project
# and writes them to npm-all.txt in "packageName, version" format.

Set-Location $PSScriptRoot

Write-Host "Running npm ls to collect all dependencies (this may take a moment)..."

# --all expands the full transitive tree; --json for structured output
# 2>$null suppresses peer-dep warnings that npm writes to stderr
$rawJson = npm ls --all --json 2>$null

if (-not $rawJson) {
    Write-Error "npm ls returned no output. Make sure 'node_modules' exists (run 'npm install' first)."
    exit 1
}

$tree = $rawJson | ConvertFrom-Json

# Recursively walk the dependency tree and collect unique "name@version" entries
$collected = [System.Collections.Generic.HashSet[string]]::new()

function Walk-Deps($node) {
    if ($null -eq $node) { return }

    $deps = $node.dependencies
    if ($null -eq $deps) { return }

    foreach ($prop in $deps.PSObject.Properties) {
        $name    = $prop.Name
        $version = $prop.Value.version

        if ($name -and $version) {
            $null = $collected.Add("${name}|${version}")
        }

        # Recurse into nested dependencies
        Walk-Deps $prop.Value
    }
}

Walk-Deps $tree

# Sort and write output
$lines = $collected | Sort-Object | ForEach-Object {
    $parts = $_ -split '\|', 2
    "$($parts[0]), $($parts[1])"
}

$outFile = Join-Path $PSScriptRoot "npm-all.txt"
$lines | Set-Content -Encoding UTF8 $outFile

Write-Host "Done. $($lines.Count) packages written to npm-all.txt"

