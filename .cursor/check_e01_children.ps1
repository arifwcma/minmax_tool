$rootDir = 'C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_extracted'

function ShowVisibility($files, $sectionLabel) {
    Write-Output ("=== " + $sectionLabel + " ===")
    foreach ($f in $files) {
        $fullPath = Join-Path $rootDir $f
        if (-not (Test-Path $fullPath)) {
            Write-Output ($f.PadRight(45) + ' -> FILE NOT FOUND')
            continue
        }
        $txt = Get-Content -Raw $fullPath
        $nameMatch = [regex]::Match($txt, '"name":"([^"]+)"')
        $name = if ($nameMatch.Success) { $nameMatch.Groups[1].Value } else { '?' }
        $typeMatch = [regex]::Match($txt, '"type":"([^"]+)"')
        $type = if ($typeMatch.Success) { $typeMatch.Groups[1].Value } else { '?' }
        $visMatch = [regex]::Match($txt, '"visibility":(true|false)')
        $vis = if ($visMatch.Success) { $visMatch.Groups[1].Value } else { '?' }
        Write-Output ($f.PadRight(45) + ' name=' + $name.PadRight(40) + ' type=' + $type.PadRight(22) + ' visibility=' + $vis)
    }
    Write-Output ''
}

$velocityChildren = @('500y.json','200y.json','100y.json','50y8.json','20y.json','10y.json','5y.json')
ShowVisibility $velocityChildren 'HW Velocity > Existing (E01) > 7 children'

$depthsChildren = @('Hors19RvDepthARI500_zerofix_tif.json','500y3.json','200y6.json','100y6.json','50y7.json','20y6.json','10y5.json','5y6.json')
ShowVisibility $depthsChildren 'HW Depths > Existing (E01) > 8 children'
