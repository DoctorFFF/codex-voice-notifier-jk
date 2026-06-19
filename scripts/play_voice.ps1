[CmdletBinding()]
param(
  [string]$AudioPath,

  [ValidateSet("Asterisk", "Beep", "Exclamation", "Hand", "Question")]
  [string]$FallbackSound = "Asterisk",

  [ValidateRange(0, 100)]
  [int]$Volume = 85,

  [ValidateRange(1, 120)]
  [int]$TimeoutSeconds = 30,

  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-VoiceLog {
  param([string]$Message)
  if (-not $Quiet) {
    Write-Host $Message
  }
}

function Play-FallbackSound {
  param([string]$Name)

  switch ($Name) {
    "Asterisk" { [System.Media.SystemSounds]::Asterisk.Play(); break }
    "Beep" { [System.Media.SystemSounds]::Beep.Play(); break }
    "Exclamation" { [System.Media.SystemSounds]::Exclamation.Play(); break }
    "Hand" { [System.Media.SystemSounds]::Hand.Play(); break }
    "Question" { [System.Media.SystemSounds]::Question.Play(); break }
    default { [System.Media.SystemSounds]::Asterisk.Play(); break }
  }

  Start-Sleep -Milliseconds 900
}

function Play-WavFile {
  param([Parameter(Mandatory = $true)][string]$Path)

  $player = New-Object System.Media.SoundPlayer $Path
  $player.PlaySync()
}

function Play-MediaFile {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][int]$Volume,
    [Parameter(Mandatory = $true)][int]$TimeoutSeconds
  )

  $player = $null
  try {
    $player = New-Object -ComObject WMPlayer.OCX
    $player.settings.volume = $Volume
    $player.URL = $Path
    $player.controls.play()

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    Start-Sleep -Milliseconds 250

    while ((Get-Date) -lt $deadline) {
      if ($player.playState -eq 1) {
        break
      }
      Start-Sleep -Milliseconds 200
    }
  }
  finally {
    if ($null -ne $player) {
      try { $player.controls.stop() | Out-Null } catch {}
      try { $player.close() | Out-Null } catch {}
      [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($player)
    }
  }
}

if (-not $AudioPath -or -not (Test-Path -LiteralPath $AudioPath -PathType Leaf)) {
  Write-VoiceLog "Audio file not found. Playing fallback sound."
  Play-FallbackSound -Name $FallbackSound
  exit 0
}

$resolvedPath = (Resolve-Path -LiteralPath $AudioPath).Path
Write-VoiceLog "Playing voice notification: $resolvedPath"

$extension = [System.IO.Path]::GetExtension($resolvedPath).ToLowerInvariant()
if ($extension -eq ".wav") {
  Play-WavFile -Path $resolvedPath
}
else {
  Play-MediaFile -Path $resolvedPath -Volume $Volume -TimeoutSeconds $TimeoutSeconds
}
