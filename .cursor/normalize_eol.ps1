$txt = [System.IO.File]::ReadAllText('I:\Jobs\20252026\Arif\EPS.pyt')
$normalized = $txt -replace "`r", "`r`n"
[System.IO.File]::WriteAllText('C:\Users\m.rahman\arcgis\ArcGIS\.cursor\EPS_view.py', $normalized)
Write-Output 'wrote normalized copy'
