$bytes = [System.IO.File]::ReadAllBytes('I:\Jobs\20252026\Arif\EPS.pyt')
$len = $bytes.Length
$cr = 0
$lf = 0
for ($i = 0; $i -lt $len; $i++) {
    if ($bytes[$i] -eq 13) { $cr++ }
    elseif ($bytes[$i] -eq 10) { $lf++ }
}
Write-Output ('Length: ' + $len)
Write-Output ('CR (0x0D): ' + $cr)
Write-Output ('LF (0x0A): ' + $lf)
