$ErrorActionPreference = 'Stop'

try {
    $setter = Get-WmiObject -Namespace root\WMI -Class Lenovo_SetBiosSetting
    $save = Get-WmiObject -Namespace root\WMI -Class Lenovo_SaveBiosSettings

    $setResult = $setter.SetBiosSetting('VirtualizationTechnology,Enable')
    if ($setResult.return -ne 'Success') {
        throw "Lenovo BIOS returned: $($setResult.return)"
    }

    $saveResult = $save.SaveBiosSettings()
    if ($saveResult.return -ne 'Success') {
        throw "Lenovo BIOS could not save the change: $($saveResult.return)"
    }

    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        'Virtualization has been enabled in the Lenovo firmware. Click OK; the laptop will restart in 15 seconds.',
        'Virtualization enabled',
        'OK',
        'Information'
    ) | Out-Null
    shutdown.exe /r /t 15 /c 'Restarting to apply the virtualization setting.'
}
catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "It could not change the BIOS setting.\n\n$($_.Exception.Message)\n\nA BIOS supervisor password may be set.",
        'Virtualization was not changed',
        'OK',
        'Error'
    ) | Out-Null
}
