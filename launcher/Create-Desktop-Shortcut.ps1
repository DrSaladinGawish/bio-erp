# Create-Desktop-Shortcut.ps1
# Creates a desktop shortcut + optional Start Menu pin for IncentiveHouse ERP

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ERP_HOME = "D:\ERP System\BIO_ERP"
$LAUNCHER = "$ERP_HOME\launcher\Start-IH-ERP.ps1"
$ICON_PATH = "$ERP_HOME\app\static\logo.ico"
$DESKTOP = [Environment]::GetFolderPath("Desktop")

if (-not (Test-Path $LAUNCHER)) {
    Write-Host "[ERROR] Launcher not found: $LAUNCHER" -ForegroundColor Red
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DESKTOP\IncentiveHouse ERP.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = '-ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $LAUNCHER + '"'
$Shortcut.WorkingDirectory = $ERP_HOME
$Shortcut.IconLocation = $ICON_PATH
$Shortcut.Description = "Launch IncentiveHouse ERP Server (Port 9001)"
$Shortcut.Save()

Write-Host "[OK] Desktop shortcut created!" -ForegroundColor Green
Write-Host "  Location: $DESKTOP\IncentiveHouse ERP.lnk" -ForegroundColor Gray
