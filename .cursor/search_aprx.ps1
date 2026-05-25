$txt = Get-Content -Raw 'C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_extracted\GISProject.json'
$patterns = @('\.pyt', 'EPS', 'Toolbox', 'I:\\\\Jobs', 'I:/Jobs', 'pythontoolbox', 'CIMToolbox', 'toolboxes')
foreach ($p in $patterns) {
    Write-Output ('--- pattern: ' + $p + ' ---')
    $matches = [regex]::Matches($txt, $p)
    Write-Output ('count: ' + $matches.Count)
    foreach ($m in $matches) {
        $start = [Math]::Max(0, $m.Index - 200)
        $len = [Math]::Min(450, $txt.Length - $start)
        Write-Output ('--- match at ' + $m.Index + ' ---')
        Write-Output $txt.Substring($start, $len)
    }
}
