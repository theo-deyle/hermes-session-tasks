#Requires -Version 7.0
<#
.SYNOPSIS
Install plugin.js, the Desktop half of the hermes-session-tasks plugin, on this machine.

.DESCRIPTION
Run this script with PowerShell 7 on each Hermes Desktop machine. It copies plugin.js from devpc
with scp into the Desktop plugin folder of this machine. Desktop loads the disk copy within
seconds. The copy goes to a temp file first. The script moves the temp file over plugin.js only
when the temp file holds "export default". Run the script again to update.

.PARAMETER HermesHome
A full path to the Hermes home of this machine. The default is the home that Desktop uses.

.PARAMETER DevpcHost
The SSH name of devpc on this machine. The default is devpc.

.PARAMETER DryRun
Print the home, the slot and the source, and write nothing.

.EXAMPLE
pwsh -NoProfile -File ./install-desktop.ps1 -DevpcHost devpc

Install on the Mac.

.EXAMPLE
pwsh -NoProfile -File .\install-desktop.ps1 -DevpcHost devpc -DryRun

Show the plan on the Windows PC and write nothing.
#>
[CmdletBinding()]
param(
  [string]$HermesHome = '',
  [string]$DevpcHost = 'devpc',
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PluginId = 'hermes-session-tasks'
$RemotePath = '/home/theo/local_repo/hermes-session-tasks/plugin/desktop/plugin.js'
$TempName = '.plugin.js.new'

function Write-Problem {
  param([string]$Message)
  [Console]::Error.WriteLine("error: $Message")
}

function Get-DesktopHome {
  return $HermesHome
}

function Copy-RemoteFile {
  param([string]$Source, [string]$Target)
  # Tailscale SSH has no SFTP subsystem, so the SFTP transfer of OpenSSH 9 can end with
  # "Connection closed". The -O flag selects the legacy scp protocol. An OpenSSH client older
  # than 9.0 rejects -O and already uses the legacy protocol, so the plain call runs then.
  & scp -O -q $Source $Target 2>$null
  if ($LASTEXITCODE -eq 0) { return $true }
  & scp -q $Source $Target
  return ($LASTEXITCODE -eq 0)
}

function Install-PanePlugin {
  param([string]$DesktopHome, [string]$DevpcHost)
  $slot = Join-Path (Join-Path $DesktopHome 'desktop-plugins') $PluginId
  $target = Join-Path $slot 'plugin.js'
  $temp = Join-Path $slot $TempName
  Write-Host "home: $DesktopHome"
  Write-Host "slot: $slot"
  Write-Host "copy: ${DevpcHost}:$RemotePath"
  New-Item -ItemType Directory -Path $slot -Force | Out-Null
  $moved = $false
  try {
    # A relative target name keeps a Windows drive letter from reading as a host.
    Push-Location -LiteralPath $slot
    $moved = $true
    if (-not (Copy-RemoteFile "${DevpcHost}:$RemotePath" $TempName)) {
      Write-Problem "scp failed for ${DevpcHost}:$RemotePath, so plugin.js is unchanged"
      return 1
    }
    if (-not (Select-String -LiteralPath $temp -Pattern 'export default' -SimpleMatch -Quiet)) {
      Write-Problem "the copied file has no 'export default', so it is not a plugin"
      return 1
    }
    Move-Item -LiteralPath $temp -Destination $target -Force
    $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "installed: $target"
    Write-Host "sha256: $hash"
    return 0
  } finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
    if ($moved) { Pop-Location }
  }
}

function Invoke-Main {
  $desktopHome = Get-DesktopHome
  return (Install-PanePlugin -DesktopHome $desktopHome -DevpcHost $DevpcHost)
}

if ($MyInvocation.InvocationName -ne '.') { exit (Invoke-Main) }
