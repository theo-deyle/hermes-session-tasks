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

.PARAMETER RemotePath
The full path of the file to install, on devpc. The default is plugin/desktop/plugin.js in the devpc checkout.

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
  [string]$RemotePath = '/home/theo/local_repo/hermes-session-tasks/plugin/desktop/plugin.js',
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PluginId = 'hermes-session-tasks'
$TempName = '.plugin.js.new'

function Write-Problem {
  param([string]$Message)
  [Console]::Error.WriteLine("error: $Message")
}

function Get-HomeRoot {
  # Desktop maps a home inside a "profiles" folder to the parent of that folder.
  param([string]$Path)
  $full = [System.IO.Path]::GetFullPath($Path)
  $trimmed = $full.TrimEnd([char]'/', [char]'\')
  if ($trimmed -eq '') { return $full }
  $parent = [System.IO.Path]::GetDirectoryName($trimmed)
  if ($parent -and ([System.IO.Path]::GetFileName($parent) -ieq 'profiles')) {
    return [System.IO.Path]::GetDirectoryName($parent)
  }
  return $trimmed
}

function Resolve-HermesHome {
  # The home rule of Desktop (apps/desktop/electron/data-paths.mjs). Every input is a parameter,
  # so a test can reach the Windows branch on Linux.
  param(
    [string]$EnvHome = '',
    [bool]$OnWindows = $false,
    [string]$RegistryHome = '',
    [string]$LocalAppData = '',
    [string]$UserHome = '',
    [string]$Suffix = '',
    [bool]$DefaultExists = $false,
    [bool]$LegacyExists = $false
  )
  if ($EnvHome) { return Get-HomeRoot $EnvHome }
  if ($OnWindows) {
    if ($RegistryHome) { return Get-HomeRoot $RegistryHome }
    $default = (Join-Path $LocalAppData 'hermes') + $Suffix
    # The legacy home applies to an ordinary install only: no suffix, no default folder yet.
    if ((-not $Suffix) -and (-not $DefaultExists) -and $LegacyExists) {
      return Join-Path $UserHome '.hermes'
    }
    return $default
  }
  return (Join-Path $UserHome '.hermes') + $Suffix
}

function Get-DesktopHome {
  if ($HermesHome) {
    if (-not [System.IO.Path]::IsPathRooted($HermesHome)) {
      Write-Problem "HermesHome must be a full path, not '$HermesHome'"
      return $null
    }
    return $HermesHome
  }
  $envHome = [Environment]::GetEnvironmentVariable('HERMES_HOME')
  $onWindows = [bool]$IsWindows
  $registryHome = ''
  if ($onWindows -and ($null -eq $envHome)) {
    # Explorer can miss a setx change, so Desktop reads the user registry value too.
    $registryHome = [string](Get-ItemPropertyValue -Path 'HKCU:\Environment' -Name 'HERMES_HOME' -ErrorAction SilentlyContinue)
  }
  $localAppData = "$env:LOCALAPPDATA".Trim()
  if (-not $localAppData) { $localAppData = Join-Path $HOME 'AppData\Local' }
  $suffix = "$env:HERMES_DATA_DIR_SUFFIX"
  $defaultHome = (Join-Path $localAppData 'hermes') + $suffix
  return Resolve-HermesHome `
    -EnvHome "$envHome" -OnWindows $onWindows -RegistryHome $registryHome `
    -LocalAppData $localAppData -UserHome $HOME -Suffix $suffix `
    -DefaultExists (Test-Path -LiteralPath $defaultHome) `
    -LegacyExists (Test-Path -LiteralPath (Join-Path $HOME '.hermes'))
}

function Test-DevpcHost {
  param([string]$Name)
  if ([string]::IsNullOrEmpty($Name)) { return $false }
  if ($Name.StartsWith('-')) { return $false }
  return ($Name -match '^[A-Za-z0-9._@-]+\z')
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
  param([string]$DesktopHome, [string]$DevpcHost, [switch]$DryRun)
  $slot = Join-Path (Join-Path $DesktopHome 'desktop-plugins') $PluginId
  $target = Join-Path $slot 'plugin.js'
  $temp = Join-Path $slot $TempName
  Write-Host "home: $DesktopHome"
  Write-Host "slot: $slot"
  Write-Host "copy: ${DevpcHost}:$RemotePath"
  if ($DryRun) {
    Write-Host 'dry run: nothing written'
    return 0
  }
  if (Test-Path -LiteralPath $target -PathType Container) {
    Write-Problem "refusing to replace ${target}: it is a directory"
    return 1
  }
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
  if (-not (Test-DevpcHost -Name $DevpcHost)) {
    Write-Problem "refusing DevpcHost '$DevpcHost': use only letters, digits, '.', '_', '@', '-', and no leading '-'"
    return 1
  }
  $desktopHome = Get-DesktopHome
  if (-not $desktopHome) { return 1 }
  return (Install-PanePlugin -DesktopHome $desktopHome -DevpcHost $DevpcHost -DryRun:$DryRun)
}

if ($MyInvocation.InvocationName -ne '.') { exit (Invoke-Main) }
