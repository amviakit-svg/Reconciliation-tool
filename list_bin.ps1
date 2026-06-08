$shell = New-Object -ComObject Shell.Application
$recycleBin = $shell.Namespace(10)
foreach ($item in $recycleBin.Items()) {
    Write-Output "Found in Recycle Bin: $($item.Name) at $($item.Path)"
}
