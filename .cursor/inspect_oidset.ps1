$bytes = [System.IO.File]::ReadAllBytes('C:\Users\m.rahman\arcgis\ArcGIS\.cursor\flood_mapping_extracted\ObjectIdentifierSet\8fd72d04c72e395fa50375d1ebb55127.dat')
Write-Output ('length: ' + $bytes.Length)
Write-Output ('hex: ' + (($bytes | ForEach-Object { '{0:X2}' -f $_ }) -join ' '))
if ($bytes.Length -ge 4) {
    $count = [System.BitConverter]::ToInt32($bytes, 0)
    Write-Output ('first int32: ' + $count)
}
$cursor = 4
$oid_index = 0
while ($cursor + 4 -le $bytes.Length) {
    $val = [System.BitConverter]::ToInt32($bytes, $cursor)
    Write-Output ('OID[' + $oid_index + '] @offset ' + $cursor + ': ' + $val)
    $cursor += 4
    $oid_index++
}
