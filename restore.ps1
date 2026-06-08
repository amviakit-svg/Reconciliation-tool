$shell = New-Object -ComObject Shell.Application
$recycleBin = $shell.Namespace(10)
foreach ($item in $recycleBin.Items()) {
    if ($item.Name -like '*metadata.db*') {
        Write-Output "Restoring: $($item.Path)"
        $item.InvokeVerb('undelete')
    }
}
