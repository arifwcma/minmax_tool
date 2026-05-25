$mapDir = 'C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_extracted\map'

$files = @(
    'Climate_Change___Scenario_1__IRI10_.json',
    'Rain_on_Grid.json',
    'Climate_Change___Scenario_1__IRI10_2.json',
    'Rain_on_Grid2.json'
)

foreach ($f in $files) {
    $fullPath = Join-Path $mapDir $f
    if (-not (Test-Path $fullPath)) {
        Write-Host ('FILE NOT FOUND: ' + $f)
        continue
    }
    $txt = Get-Content -Raw $fullPath
    $name = ([regex]::Match($txt, '"name":"([^"]+)"')).Groups[1].Value
    $type = ([regex]::Match($txt, '"type":"([^"]+)"')).Groups[1].Value
    $vis  = ([regex]::Match($txt, '"visibility":(true|false)')).Groups[1].Value
    Write-Host ($f.PadRight(45) + ' name=' + $name.PadRight(40) + ' type=' + $type.PadRight(22) + ' visibility=' + $vis)
    $childMatches = [regex]::Matches($txt, '"layers":\[([^\]]+)\]')
    if ($childMatches.Count -gt 0) {
        Write-Host ('  children: ' + $childMatches[0].Groups[1].Value)
    }
}
