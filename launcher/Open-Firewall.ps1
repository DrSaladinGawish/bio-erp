# ============================================================================
#  Open Windows Firewall ports for IncentiveHouse ERP (LAN access)
#  MUST be run as Administrator!  (Right-click PowerShell -> Run as admin)
#  Run:  powershell -File Open-Firewall.ps1
# ============================================================================
$ErrorActionPreference = "Stop"

# Self-elevate if not already admin
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERROR] This script MUST run as Administrator!" -ForegroundColor Red
    Write-Host "  Right-click PowerShell -> 'Run as Administrator', then re-run." -ForegroundColor Yellow
    pause
    exit 1
}

$rules = @(
    @{
        Name    = "IH-ERP-9001"
        Display = "IncentiveHouse ERP (Port 9001)"
        Port    = 9001
    },
    @{
        Name    = "IH-ERP-Nginx-80"
        Display = "IncentiveHouse ERP Nginx (Port 80)"
        Port    = 80
    }
)

foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Display -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  [OK ] Rule already exists: $($r.Display)" -ForegroundColor Green
    } else {
        try {
            New-NetFirewallRule -DisplayName $r.Display `
                -Direction Inbound `
                -Protocol TCP `
                -LocalPort $r.Port `
                -Action Allow `
                -Profile Any `
                -Enabled True | Out-Null
            Write-Host "  [NEW] Created rule: $($r.Display) on port $($r.Port)" -ForegroundColor Green
        } catch {
            Write-Host "  [ERR] Failed to create rule for port $($r.Port): $_" -ForegroundColor Red
        }
    }
}

# Also try the legacy netsh approach (in case New-NetFirewallRule is unavailable)
foreach ($r in $rules) {
    $cmd = "advfirewall firewall add rule name=`"$($r.Display)`" dir=in action=allow protocol=TCP localport=$($r.Port)"
    cmd /c $cmd 2>&1 | Out-Null
}

# Show this PC's IP addresses
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Firewall ports opened!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  This PC's IP addresses:" -ForegroundColor Yellow
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -notlike "127.*" -and
    $_.IPAddress -notlike "169.254.*"
} | ForEach-Object { "    " + $_.IPAddress + "  (" + $_.InterfaceAlias + ")" }
Write-Host ($ips -join "`n")
Write-Host ""
Write-Host "  Other devices on the same WiFi/Ethernet can now reach:" -ForegroundColor Yellow
Write-Host "    http://<ip>:9001   (main ERP)" -ForegroundColor White
Write-Host "    http://<ip>        (via nginx on port 80)" -ForegroundColor White
Write-Host ""
Write-Host "  If still not reachable, check:" -ForegroundColor Yellow
Write-Host "    1. Both devices on the same network (same SSID/subnet)" -ForegroundColor White
Write-Host "    2. Antivirus not blocking port 9001" -ForegroundColor White
Write-Host "    3. Windows Defender Firewall rules show 'Allow' (not Block)" -ForegroundColor White
Write-Host ""
