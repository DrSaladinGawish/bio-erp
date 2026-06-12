# IncentiveHouse ERP - Launcher & Remote Access Package

All files in this directory (`D:\ERP System\BIO_ERP\launcher\`) are **infrastructure only** - they do NOT modify any application code.

## Files in this package

| File | Purpose |
|------|---------|
| `Start-IH-ERP.bat` | Command-line launcher (shows server log) |
| `Start-IH-ERP.ps1` | GUI launcher (dark theme, Start/Stop/Docker buttons) |
| `Create-Desktop-Shortcut.ps1` | Creates `IncentiveHouse ERP.lnk` on your desktop |
| `docker-compose-remote.yml` | Docker config that binds 0.0.0.0:9001 + nginx on port 80 |
| `nginx-remote.conf` | Reverse proxy config (port 80 -> 9001) |
| `Update-Docker-Remote.ps1` | One-command swap from local to remote compose |
| `Open-Firewall.ps1` | Opens Windows Firewall ports 9001 and 80 |

---

## Quick Start (5 minutes)

### 1. Native Python (Recommended for dev)
```powershell
# Open the GUI
powershell -ExecutionPolicy Bypass -File "D:\ERP System\BIO_ERP\launcher\Start-IH-ERP.ps1"
# Click START
# Browser opens http://localhost:9001/

# Or use the .bat (cmd window with live log)
cmd /c "D:\ERP System\BIO_ERP\launcher\Start-IH-ERP.bat"
```

### 2. Desktop Icon (one-time setup)
```powershell
powershell -ExecutionPolicy Bypass -File "D:\ERP System\BIO_ERP\launcher\Create-Desktop-Shortcut.ps1"
```
Then **double-click "IncentiveHouse ERP" on your desktop**.

---

## Remote Access (10 minutes)

Make the ERP reachable from phones/laptops on the same WiFi.

### Step 1: Install Docker Desktop (if not installed)
Download: https://www.docker.com/products/docker-desktop/

### Step 2: Update docker-compose to remote mode
```powershell
cd "D:\ERP System\BIO_ERP"
powershell -ExecutionPolicy Bypass -File ".\launcher\Update-Docker-Remote.ps1"
```
This:
- Backs up the original `docker-compose.yml` to `docker-compose.yml.bak.local`
- Replaces it with the LAN-accessible version
- Copies `nginx.conf` to the project root

### Step 3: Open Windows Firewall (run as Administrator)
Right-click PowerShell -> **Run as Administrator**, then:
```powershell
powershell -ExecutionPolicy Bypass -File "D:\ERP System\BIO_ERP\launcher\Open-Firewall.ps1"
```
This opens TCP ports 9001 and 80, and prints your PC's IP addresses.

### Step 4: Find your PC's IP
```powershell
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -like "*Ethernet*" -or $_.InterfaceAlias -like "*Wi-Fi*" } |
    Select-Object InterfaceAlias, IPAddress
```
Example output: `192.168.1.45`

### Step 5: Start Docker
```powershell
cd "D:\ERP System\BIO_ERP"
docker-compose up --build
```

### Step 6: Open from another device
On the same WiFi, open browser to:
- `http://192.168.1.45:9001` (direct ERP)
- `http://192.168.1.45` (via nginx, port 80)

---

## Architecture

```
[Phone/Laptop/Other PC on WiFi]
            |
            |  http://192.168.1.45:9001  OR  http://192.168.1.45
            v
[Windows Firewall - ports 9001, 80]   <-- opened by Open-Firewall.ps1
            |
            v
[Windows Host - D:\ERP System\BIO_ERP]
            |
            +-- Option A (Native): Start-IH-ERP.bat / .ps1
            |       -> uvicorn app.main:app --host 0.0.0.0 --port 9001
            |
            +-- Option B (Docker): docker-compose up
                    -> ih-erp-app    : container on 0.0.0.0:9001
                    -> ih-erp-nginx  : reverse proxy on 0.0.0.0:80 -> :9001
```

---

## Troubleshooting

### "Connection refused" from another device
1. Verify the server is running: open `http://localhost:9001/` on the host
2. Verify firewall rules: `Get-NetFirewallRule -DisplayName "IH-ERP*"`
3. Verify IP: `ipconfig` (look for IPv4 Address, NOT 127.0.0.1)
4. Verify the other device is on the **same SSID** (not a guest network)
5. Try temporarily disabling the firewall to test: `Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False` (re-enable after!)

### "This PC's IP keeps changing"
Set a static IP in Windows:
- Settings -> Network & Internet -> Wi-Fi / Ethernet -> your adapter
- IP assignment -> Edit -> Manual -> IPv4 ON
- IP: 192.168.1.45, Subnet: 255.255.255.0, Gateway: 192.168.1.1

Or configure DHCP reservation on your router for the host's MAC address.

### "Docker not found"
Install Docker Desktop: https://www.docker.com/products/docker-desktop/
Then restart PowerShell.

### Server won't start - "port already in use"
```powershell
# Find what's using port 9001
netstat -ano | findstr ":9001 "
# Kill it (replace PID with the actual number)
taskkill /F /PID <PID>
```

### Want to use a different port
Edit `Start-IH-ERP.ps1` and `Start-IH-ERP.bat`, change the `$PORT = 9001` and `set PORT=9001` lines.
Then update `Open-Firewall.ps1` and `docker-compose-remote.yml` with the new port.

---

## Undo / Revert to Localhost-Only

```powershell
# Restore original docker-compose
cd "D:\ERP System\BIO_ERP"
Copy-Item docker-compose.yml.bak.local docker-compose.yml -Force

# Remove firewall rules
Remove-NetFirewallRule -DisplayName "IH-ERP-9001"
Remove-NetFirewallRule -DisplayName "IH-ERP-Nginx-80"
```
