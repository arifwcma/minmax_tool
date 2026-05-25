Add-Type -AssemblyName System.IO.Compression.FileSystem
$src = 'C:\Users\m.rahman\arcgis\ArcGIS\FLood Mapping.aprx'
$tmp = 'C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_copy.zip'
$extractDir = 'C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_extracted'
Copy-Item -Path $src -Destination $tmp -Force
if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
$zip = [System.IO.Compression.ZipFile]::OpenRead($tmp)
foreach ($entry in $zip.Entries) {
    Write-Output ($entry.FullName + ' | ' + $entry.Length)
}
$zip.Dispose()
[System.IO.Compression.ZipFile]::ExtractToDirectory($tmp, $extractDir)
Write-Output "EXTRACTED TO: $extractDir"
