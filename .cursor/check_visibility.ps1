$mapDir = 'C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_extracted\map'

function ShowVisibility($files, $sectionLabel) {
    Write-Output ("=== " + $sectionLabel + " ===")
    foreach ($f in $files) {
        $fullPath = Join-Path $mapDir $f
        if (-not (Test-Path $fullPath)) {
            Write-Output ($f.PadRight(45) + ' -> FILE NOT FOUND')
            continue
        }
        $txt = Get-Content -Raw $fullPath
        $nameMatch = [regex]::Match($txt, '"name":"([^"]+)"')
        $name = if ($nameMatch.Success) { $nameMatch.Groups[1].Value } else { '?' }
        $visMatch = [regex]::Match($txt, '"visibility":(true|false)')
        $vis = if ($visMatch.Success) { $visMatch.Groups[1].Value } else { '?' }
        Write-Output ($f.PadRight(45) + ' name=' + $name.PadRight(35) + ' visibility=' + $vis)
    }
    Write-Output ''
}

$heightRasters = @(
    'Hors19RvWSEARI5_tif.json',
    'Hors19RvWSEARI10_tif.json',
    'Hors19RvWSEARI20_tif.json',
    'Hors19RvWSEARI50_tif.json',
    'Hors19RvWSEARI100_tif.json',
    'Hors19RvWSEARI100IRI10_tif.json',
    'Hors19RvWSEARI200_tif.json',
    'Hors19RvWSEARI500_tif.json',
    'Hors19RvWSEARI500IRI10_tif.json'
)
ShowVisibility $heightRasters 'Heights group children (9 rasters)'

ShowVisibility @('New_Group_Layer4.json') 'Heights group itself'

ShowVisibility @('HorshamWartook___Velocity.json') 'HorshamWartook - Velocity group itself'
ShowVisibility @('Existing__E01_10.json') 'HW Velocity > Existing (E01) child group'

ShowVisibility @('HorshamWartook___Depths2.json') 'HorshamWartook - Depths group itself'
ShowVisibility @('Existing__E01_9.json') 'HW Depths > Existing (E01) child group'
