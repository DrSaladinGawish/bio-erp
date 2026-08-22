# ============================================================================
#  IncentiveHouse ERP - GUI System Launcher (PowerShell + WPF)
#  Launches the server and verifies ALL modules are healthy.
# ============================================================================
param()

Add-Type -AssemblyName PresentationFramework
$BASE_DIR = "D:\ERP System\BIO_ERP"
$PORT     = 8000
$LOGFILE  = "$BASE_DIR\logs\server.log"

if (-not (Test-Path "$BASE_DIR\logs")) {
    New-Item -ItemType Directory -Path "$BASE_DIR\logs" -Force | Out-Null
}

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="IncentiveHouse ERP - System Launcher v5.4 + Part 4" Height="780" Width="960"
        Background="#1E1E1E" Foreground="#E8E8E8"
        WindowStartupLocation="CenterScreen" ResizeMode="CanMinimize">
  <Window.Resources>
    <Style TargetType="Button">
      <Setter Property="Background" Value="#2D2D30"/>
      <Setter Property="Foreground" Value="#E8E8E8"/>
      <Setter Property="BorderBrush" Value="#D4A017"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Padding" Value="14,8"/>
      <Setter Property="Margin" Value="6"/>
      <Setter Property="FontSize" Value="13"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
    </Style>
  </Window.Resources>
  <Grid Margin="14">
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>
    <StackPanel Grid.Row="0" Margin="0,0,0,6">
      <TextBlock Text="INCENTIVE HOUSE ERP" FontSize="22" FontWeight="Bold" Foreground="#D4A017"/>
      <TextBlock Text="v5.4  -  System Launcher  (Server + All Modules)" FontSize="11" Foreground="#999"/>
    </StackPanel>
    <Border Grid.Row="1" Background="#252526" BorderBrush="#3F3F46" BorderThickness="1" Padding="12" Margin="0,0,0,6">
      <Grid>
        <Grid.ColumnDefinitions><ColumnDefinition Width="90"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
        <Grid.RowDefinitions><RowDefinition/><RowDefinition/><RowDefinition/><RowDefinition/></Grid.RowDefinitions>
        <TextBlock Grid.Row="0" Grid.Column="0" Text="Status:" Foreground="#999"/>
        <TextBlock Grid.Row="0" Grid.Column="1" Name="TxtStatus" Text="Ready" Foreground="#4EC9B0" FontWeight="Bold"/>
        <TextBlock Grid.Row="1" Grid.Column="0" Text="Path:" Foreground="#999"/>
        <TextBlock Grid.Row="1" Grid.Column="1" Name="TxtPath" Text="$BASE_DIR"/>
        <TextBlock Grid.Row="2" Grid.Column="0" Text="Modules:" Foreground="#999"/>
        <TextBlock Grid.Row="2" Grid.Column="1" Name="TxtModules" Text="-"/>
        <TextBlock Grid.Row="3" Grid.Column="0" Text="PID:" Foreground="#999"/>
        <TextBlock Grid.Row="3" Grid.Column="1" Name="TxtPID" Text="-" Foreground="#999"/>
      </Grid>
    </Border>
    <StackPanel Grid.Row="2" Orientation="Horizontal" Margin="0,0,0,6">
      <Button Name="BtnStart" Content="START" Width="120" Background="#228B22" Foreground="#FFFFFF" BorderBrush="#228B22"/>
      <Button Name="BtnStop"  Content="STOP"  Width="100"/>
      <Button Name="BtnCheck" Content="CHECK MODULES" Width="150"/>
      <Button Name="BtnDocker" Content="DOCKER" Width="100"/>
      <Button Name="BtnBrowser" Content="BROWSER" Width="100"/>
      <Button Name="BtnClear" Content="CLEAR" Width="100"/>
      <Button Name="BtnExit"  Content="EXIT" Width="100" Background="#722F37" BorderBrush="#722F37"/>
    </StackPanel>
    <!-- Module status grid -->
    <Border Grid.Row="3" Background="#252526" BorderBrush="#3F3F46" BorderThickness="1" Padding="8" Margin="0,0,0,6">
      <Grid Name="ModuleGrid">
        <Grid.ColumnDefinitions>
          <ColumnDefinition Width="160"/>
          <ColumnDefinition Width="120"/>
          <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        <TextBlock Grid.Row="0" Grid.Column="0" Text="Module" FontWeight="Bold" Foreground="#D4A017"/>
        <TextBlock Grid.Row="0" Grid.Column="1" Text="Status" FontWeight="Bold" Foreground="#D4A017"/>
        <TextBlock Grid.Row="0" Grid.Column="2" Text="Details" FontWeight="Bold" Foreground="#D4A017"/>
        <TextBlock Grid.Row="1" Grid.Column="0" Text="Server Health"/>
        <TextBlock Grid.Row="1" Grid.Column="1" Name="M0S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="1" Grid.Column="2" Name="M0D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="2" Grid.Column="0" Text="GRN (Goods Receipt)"/>
        <TextBlock Grid.Row="2" Grid.Column="1" Name="M1S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="2" Grid.Column="2" Name="M1D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="3" Grid.Column="0" Text="Cost Mgmt"/>
        <TextBlock Grid.Row="3" Grid.Column="1" Name="M2S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="3" Grid.Column="2" Name="M2D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="4" Grid.Column="0" Text="Event Budget"/>
        <TextBlock Grid.Row="4" Grid.Column="1" Name="M3S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="4" Grid.Column="2" Name="M3D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="5" Grid.Column="0" Text="BSC"/>
        <TextBlock Grid.Row="5" Grid.Column="1" Name="M4S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="5" Grid.Column="2" Name="M4D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="6" Grid.Column="0" Text="BI / Neural"/>
        <TextBlock Grid.Row="6" Grid.Column="1" Name="M5S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="6" Grid.Column="2" Name="M5D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="7" Grid.Column="0" Text="IH Budget"/>
        <TextBlock Grid.Row="7" Grid.Column="1" Name="M6S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="7" Grid.Column="2" Name="M6D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="8" Grid.Column="0" Text="IH Approval"/>
        <TextBlock Grid.Row="8" Grid.Column="1" Name="M7S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="8" Grid.Column="2" Name="M7D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="9" Grid.Column="0" Text="Sales (SAL)"/>
        <TextBlock Grid.Row="9" Grid.Column="1" Name="M8S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="9" Grid.Column="2" Name="M8D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="10" Grid.Column="0" Text="Purchases (PUR)"/>
        <TextBlock Grid.Row="10" Grid.Column="1" Name="M9S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="10" Grid.Column="2" Name="M9D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="11" Grid.Column="0" Text="Events (EVN)"/>
        <TextBlock Grid.Row="11" Grid.Column="1" Name="M10S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="11" Grid.Column="2" Name="M10D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="12" Grid.Column="0" Text="EBA - Gap Scanner"/>
        <TextBlock Grid.Row="12" Grid.Column="1" Name="M11S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="12" Grid.Column="2" Name="M11D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="13" Grid.Column="0" Text="EBA - Health Monitor"/>
        <TextBlock Grid.Row="13" Grid.Column="1" Name="M12S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="13" Grid.Column="2" Name="M12D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="14" Grid.Column="0" Text="EBA - Bilingual Chat"/>
        <TextBlock Grid.Row="14" Grid.Column="1" Name="M13S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="14" Grid.Column="2" Name="M13D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="15" Grid.Column="0" Text="EBA - Auto-Remediation"/>
        <TextBlock Grid.Row="15" Grid.Column="1" Name="M14S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="15" Grid.Column="2" Name="M14D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="16" Grid.Column="0" Text="EBA - Library Compliance"/>
        <TextBlock Grid.Row="16" Grid.Column="1" Name="M15S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="16" Grid.Column="2" Name="M15D" Text="" Foreground="#999"/>
        <TextBlock Grid.Row="17" Grid.Column="0" Text="EBA - Vibe Coding Agent"/>
        <TextBlock Grid.Row="17" Grid.Column="1" Name="M16S" Text="..." Foreground="#999"/>
        <TextBlock Grid.Row="17" Grid.Column="2" Name="M16D" Text="" Foreground="#999"/>
      </Grid>
    </Border>
    <!-- Part 4 Data Flow Dashboard Status -->
    <Border Grid.Row="4" Background="#0a1a2a" BorderBrush="#06b6d4" BorderThickness="1" Padding="8" Margin="0,0,0,4">
      <Grid>
        <Grid.ColumnDefinitions><ColumnDefinition Width="160"/><ColumnDefinition Width="*"/><ColumnDefinition Width="140"/></Grid.ColumnDefinitions>
        <TextBlock Grid.Column="0" Text="🌊 Part 4 Dashboard" FontWeight="Bold" Foreground="#06b6d4" VerticalAlignment="Center"/>
        <StackPanel Grid.Column="1" Orientation="Horizontal">
          <TextBlock Name="TxtPart4Status" Text="⏳ Starting..." Foreground="#999" VerticalAlignment="Center" Margin="0,0,12,0"/>
          <TextBlock Name="TxtPart4Version" Text="" Foreground="#666" FontSize="10" VerticalAlignment="Center"/>
        </StackPanel>
        <Button Grid.Column="2" Name="BtnPart4Dashboard" Content="🌊 Open Dashboard" Background="#06b6d4" Foreground="White" BorderBrush="#06b6d4" Padding="8,4" HorizontalAlignment="Right"/>
      </Grid>
    </Border>
    <Border Grid.Row="5" Background="#0C0C0C" BorderBrush="#3F3F46" BorderThickness="1">
      <ScrollViewer Name="LogScroll" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto">
        <TextBlock Name="TxtLog" Padding="10" FontFamily="Consolas" FontSize="11" Foreground="#DCDCDC" TextWrapping="NoWrap"/>
      </ScrollViewer>
    </Border>
    <TextBlock Grid.Row="6" Name="TxtFooter" Margin="0,8,0,0" FontSize="10" Foreground="#666"/>
  </Grid>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)

$txtStatus  = $window.FindName("TxtStatus")
$txtPath    = $window.FindName("TxtPath")
$txtModules = $window.FindName("TxtModules")
$txtPID     = $window.FindName("TxtPID")
$txtLog     = $window.FindName("TxtLog")
$txtFooter  = $window.FindName("TxtFooter")
$btnStart   = $window.FindName("BtnStart")
$btnStop    = $window.FindName("BtnStop")
$btnCheck   = $window.FindName("BtnCheck")
$btnDocker  = $window.FindName("BtnDocker")
$btnBrowser = $window.FindName("BtnBrowser")
$btnClear   = $window.FindName("BtnClear")
$btnExit    = $window.FindName("BtnExit")
$btnPart4   = $window.FindName("BtnPart4Dashboard")
$logScroll  = $window.FindName("LogScroll")

$txtPart4Status  = $window.FindName("TxtPart4Status")
$txtPart4Version = $window.FindName("TxtPart4Version")

$txtFooter.Text = "Log: $LOGFILE"

$script:serverProcess = $null
$script:part4Process = $null

function Write-Log([string]$msg, [string]$color = "#DCDCDC") {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    $run = [Windows.Documents.Run]::new($line + "`n")
    $run.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString($color)
    $txtLog.Dispatcher.Invoke([Action]{ $txtLog.Inlines.Add($run); $logScroll.ScrollToEnd() })
    Add-Content -Path $LOGFILE -Value "[$ts] $msg"
}

function Test-Port([int]$port) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { $c.BeginConnect("127.0.0.1", $port, $null, $null) | Out-Null; Start-Sleep -Milliseconds 200; $r = $c.Connected; $c.Close(); return $r } catch { return $false }
}

function Get-ServerPID {
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            $cmd -like "*uvicorn*app.main*"
        } catch { $false }
    }
}

function Update-Status {
    $p = Get-ServerPID
    if ($p) {
        $txtStatus.Text = "RUNNING"; $txtStatus.Foreground = "#4EC9B0"
        $txtPID.Text = "$($p.Id)  port $PORT listening"; $txtPID.Foreground = "#4EC9B0"
    } elseif (Test-Port $PORT) {
        $txtStatus.Text = "RUNNING (unmanaged)"; $txtStatus.Foreground = "#D4A017"
        $txtPID.Text = "unknown"; $txtPID.Foreground = "#D4A017"
    } else {
        $txtStatus.Text = "Stopped"; $txtStatus.Foreground = "#999"
        $txtPID.Text = "-"; $txtPID.Foreground = "#999"
    }
}

function Check-Health {
    $mods = @(
        @{name="Server Health";  url="/health"},
        @{name="GRN (Goods Receipt)"; url="/api/v1/grn/summary"},
        @{name="Cost Mgmt";      url="/api/v1/cost/summary"},
        @{name="Event Budget";   url="/api/v1/event-budget/summary"},
        @{name="BSC";            url="/api/v1/bsc/summary"},
        @{name="BI / Neural";    url="/api/v1/bi/summary"},
        @{name="IH Budget";      url="/api/v1/ih-budget/summary"},
        @{name="IH Approval";    url="/api/v1/ih-approval/summary"},
        @{name="Sales (SAL)";    url="/api/v1/sal/summary"},
        @{name="Purchases (PUR)";url="/api/v1/pur/summary"},
        @{name="Events (EVN)";   url="/api/v1/evn/summary"},
        @{name="EBA - Gap Scanner";       url="/api/v1/ai-agent/status"},
        @{name="EBA - Health Monitor";    url="/api/v1/ai-agent/health"},
        @{name="EBA - Bilingual Chat";    url="/api/v1/ai-agent/status"},
        @{name="EBA - Auto-Remediation";  url="/api/v1/ai-agent/status"},
        @{name="EBA - Library Compliance";url="/api/v1/ai-agent/library/status"},
        @{name="EBA - Vibe Coding Agent"; url="/api/v1/ai-agent/vibe/sessions"}
    )
    $statusFields = @($window.FindName("M0S"),$window.FindName("M1S"),$window.FindName("M2S"),$window.FindName("M3S"),$window.FindName("M4S"),$window.FindName("M5S"),$window.FindName("M6S"),$window.FindName("M7S"),$window.FindName("M8S"),$window.FindName("M9S"),$window.FindName("M10S"),$window.FindName("M11S"),$window.FindName("M12S"),$window.FindName("M13S"),$window.FindName("M14S"),$window.FindName("M15S"),$window.FindName("M16S"))
    $detailFields = @($window.FindName("M0D"),$window.FindName("M1D"),$window.FindName("M2D"),$window.FindName("M3D"),$window.FindName("M4D"),$window.FindName("M5D"),$window.FindName("M6D"),$window.FindName("M7D"),$window.FindName("M8D"),$window.FindName("M9D"),$window.FindName("M10D"),$window.FindName("M11D"),$window.FindName("M12D"),$window.FindName("M13D"),$window.FindName("M14D"),$window.FindName("M15D"),$window.FindName("M16D"))

    Write-Log "Checking module health..." "#569CD6"
    $ok = 0; $warn = 0; $err = 0
    for ($i = 0; $i -lt $mods.Length; $i++) {
        $m = $mods[$i]
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:$PORT$($m.url)" -Method GET -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) {
                $statusFields[$i].Dispatcher.Invoke([Action]{ $statusFields[$i].Text = "OK"; $statusFields[$i].Foreground = "#4EC9B0" })
                $detailFields[$i].Dispatcher.Invoke([Action]{ $detailFields[$i].Text = "HTTP 200"; $detailFields[$i].Foreground = "#4EC9B0" })
                Write-Log "  [OK] $($m.name)" "#4EC9B0"; $ok++
            } else {
                $statusFields[$i].Dispatcher.Invoke([Action]{ $statusFields[$i].Text = "??"; $statusFields[$i].Foreground = "#D4A017" })
                $detailFields[$i].Dispatcher.Invoke([Action]{ $detailFields[$i].Text = "HTTP $($r.StatusCode)"; $detailFields[$i].Foreground = "#D4A017" })
                Write-Log "  [??] $($m.name) (HTTP $($r.StatusCode))" "#D4A017"; $warn++
            }
        } catch {
            $sc = try { $_.Exception.Response.StatusCode.value__ } catch { 0 }
            if ($sc -eq 0) {
                $statusFields[$i].Dispatcher.Invoke([Action]{ $statusFields[$i].Text = "TIMEOUT"; $statusFields[$i].Foreground = "#FF6B6B" })
                $detailFields[$i].Dispatcher.Invoke([Action]{ $detailFields[$i].Text = "No response"; $detailFields[$i].Foreground = "#FF6B6B" })
                Write-Log "  [ERR] $($m.name) (timeout)" "#FF6B6B"; $err++
            } else {
                $statusFields[$i].Dispatcher.Invoke([Action]{ $statusFields[$i].Text = "AUTH"; $statusFields[$i].Foreground = "#D4A017" })
                $detailFields[$i].Dispatcher.Invoke([Action]{ $detailFields[$i].Text = "HTTP $sc (auth req)"; $detailFields[$i].Foreground = "#D4A017" })
                Write-Log "  [OK] $($m.name) (auth required)" "#D4A017"; $warn++
            }
        }
    }
    $total = $ok + $warn + $err
    $txtModules.Dispatcher.Invoke([Action]{ $txtModules.Text = "$ok OK / $warn WARN / $err ERR   [$total modules]"; $txtModules.Foreground = if ($err -gt 0) { "#FF6B6B" } else { "#4EC9B0" } })
    Write-Log "Health check complete: $ok OK, $warn warning(s), $err error(s)" (if ($err -gt 0) { "#FF6B6B" } else { "#4EC9B0" })
}

function Start-Server {
    if (Get-ServerPID) { Write-Log "Server already running." "#D4A017"; return }
    Write-Log "Starting IncentiveHouse ERP on port $PORT..." "#4EC9B0"
    Set-Location $BASE_DIR
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "-m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1"
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $BASE_DIR
    $script:serverProcess = New-Object System.Diagnostics.Process
    $script:serverProcess.StartInfo = $psi
    Register-ObjectEvent -InputObject $script:serverProcess -EventName OutputDataReceived -Action {
        if ($EventArgs.Data) { $txtLog.Dispatcher.Invoke([Action]{ $r = [Windows.Documents.Run]::new("[$((Get-Date).ToString('HH:mm:ss'))] $($EventArgs.Data)`n"); $txtLog.Inlines.Add($r); $logScroll.ScrollToEnd() }) }
    } | Out-Null
    Register-ObjectEvent -InputObject $script:serverProcess -EventName ErrorDataReceived -Action {
        if ($EventArgs.Data) { $txtLog.Dispatcher.Invoke([Action]{ $r = [Windows.Documents.Run]::new("[$((Get-Date).ToString('HH:mm:ss'))] [ERR] $($EventArgs.Data)`n"); $r.Foreground = "#FF6B6B"; $txtLog.Inlines.Add($r); $logScroll.ScrollToEnd() }) }
    } | Out-Null
    try {
        $script:serverProcess.Start() | Out-Null
        $script:serverProcess.BeginOutputReadLine()
        $script:serverProcess.BeginErrorReadLine()
        Write-Log "Server PID $($script:serverProcess.Id)" "#4EC9B0"
        Start-Sleep -Seconds 3
        Check-Health
        Start-Part4
        Start-Process "http://localhost:$PORT/"
    } catch {
        Write-Log "Failed to start: $_" "#FF6B6B"
    }
    Update-Status
}

function Stop-Server {
    $p = Get-ServerPID
    if ($p) {
        Write-Log "Stopping PID $($p.Id)..." "#D4A017"
        try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Start-Sleep -Seconds 2; Write-Log "Stopped." "#D4A017" }
        catch { Write-Log "Failed: $_" "#FF6B6B" }
        for ($i = 0; $i -le 16; $i++) {
            $sf = $window.FindName("M${i}S"); if ($sf) { $sf.Dispatcher.Invoke([Action]{ $sf.Text = "---"; $sf.Foreground = "#999" }) }
            $df = $window.FindName("M${i}D"); if ($df) { $df.Dispatcher.Invoke([Action]{ $df.Text = ""; $df.Foreground = "#999" }) }
        }
        $txtModules.Dispatcher.Invoke([Action]{ $txtModules.Text = "-" })
    } else { Write-Log "No server running." "#999" }
    Stop-Part4
    Update-Status
}

function Start-Part4 {
    $part4Path = "$BASE_DIR\app\organs\incentivehouse_organ\launcher_dashboard_v4_0.py"
    if (-not (Test-Path $part4Path)) {
        Write-Log "Part 4 not found at $part4Path — skipping." "#D4A017"
        $txtPart4Status.Dispatcher.Invoke([Action]{ $txtPart4Status.Text = "[!] Not installed"; $txtPart4Status.Foreground = "#D4A017" })
        return
    }
    if ($script:part4Process -and (-not $script:part4Process.HasExited)) {
        Write-Log "Part 4 already running (PID $($script:part4Process.Id))." "#4EC9B0"
        return
    }
    Write-Log "Starting Part 4 Dashboard (port 9003)..." "#06b6d4"
    $psi4 = New-Object System.Diagnostics.ProcessStartInfo
    $psi4.FileName = "python"
    $psi4.Arguments = "`"$part4Path`""
    $psi4.RedirectStandardOutput = $true
    $psi4.RedirectStandardError = $true
    $psi4.UseShellExecute = $false
    $psi4.CreateNoWindow = $true
    $psi4.WorkingDirectory = "$BASE_DIR\app\organs\incentivehouse_organ"
    $script:part4Process = New-Object System.Diagnostics.Process
    $script:part4Process.StartInfo = $psi4
    $script:part4Process.Start() | Out-Null
    $script:part4Process.BeginOutputReadLine()
    $script:part4Process.BeginErrorReadLine()
    Write-Log "Part 4 PID $($script:part4Process.Id)" "#06b6d4"
    $txtPart4Status.Dispatcher.Invoke([Action]{ $txtPart4Status.Text = "[ON] Starting..."; $txtPart4Status.Foreground = "#06b6d4" })
}

function Stop-Part4 {
    if ($script:part4Process -and (-not $script:part4Process.HasExited)) {
        Write-Log "Stopping Part 4 (PID $($script:part4Process.Id))..." "#D4A017"
        try { Stop-Process -Id $script:part4Process.Id -Force -ErrorAction Stop; Write-Log "Part 4 stopped." "#D4A017" }
        catch { Write-Log "Part 4 stop failed: $_" "#FF6B6B" }
        $script:part4Process = $null
    }
    $txtPart4Status.Dispatcher.Invoke([Action]{ $txtPart4Status.Text = "[OFF] Stopped"; $txtPart4Status.Foreground = "#999" })
    $txtPart4Version.Dispatcher.Invoke([Action]{ $txtPart4Version.Text = "" })
}

function Start-Docker {
    Write-Log "Launching Docker Compose..." "#569CD6"
    Set-Location $BASE_DIR
    try {
        Start-Process cmd.exe -ArgumentList "/c cd /d $BASE_DIR & docker-compose up"
        Write-Log "Docker launched in new window." "#569CD6"
    } catch { Write-Log "Docker not found." "#FF6B6B" }
}

$btnPart4.Add_Click({ Start-Process "http://localhost:9003" })
$btnStart.Add_Click({ Start-Server })
$btnStop.Add_Click({ Stop-Server })
$btnCheck.Add_Click({
    if (Test-Port $PORT) { Check-Health } else { Write-Log "Server is not running." "#D4A017" }
})
$btnDocker.Add_Click({ Start-Docker })
$btnBrowser.Add_Click({ Start-Process "http://localhost:$PORT/" })
$btnClear.Add_Click({ $txtLog.Dispatcher.Invoke([Action]{ $txtLog.Inlines.Clear() }) })
$btnExit.Add_Click({
    if (Get-ServerPID) {
        $r = [System.Windows.MessageBox]::Show("Server is still running. Stop before exiting?","IH ERP","YesNo","Question")
        if ($r -eq "Yes") { Stop-Server; Start-Sleep -Seconds 2 }
    }
    $window.Close()
})

$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(2)
$timer.Add_Tick({ Update-Status })
$timer.Start()

# Part 4 health check timer
$part4Timer = New-Object System.Windows.Threading.DispatcherTimer
$part4Timer.Interval = [TimeSpan]::FromSeconds(5)
$part4Timer.Add_Tick({
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:9003" -TimeoutSec 2 -ErrorAction Stop
        $ver = if ($r.version) { "v$($r.version)" } else { "" }
        $txtPart4Status.Dispatcher.Invoke([Action]{
            $txtPart4Status.Text = "[ON] Online $ver"
            $txtPart4Status.Foreground = "#4EC9B0"
        })
    } catch {
        $txtPart4Status.Dispatcher.Invoke([Action]{
            if ($script:part4Process -and (-not $script:part4Process.HasExited)) {
                $txtPart4Status.Text = "[WAIT] Starting..."; $txtPart4Status.Foreground = "#D4A017"
            } else {
                $txtPart4Status.Text = "[OFF] Offline"; $txtPart4Status.Foreground = "#999"
            }
        })
    }
})
$part4Timer.Start()

Write-Log "IncentiveHouse ERP System Launcher v5.4 + Part4 ready."
Write-Log "Click START to launch server + auto-check all modules."
Update-Status

[void]$window.ShowDialog()
