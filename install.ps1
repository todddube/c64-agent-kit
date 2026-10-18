<#
.SYNOPSIS
  Install the c64-agent-kit skills for your AI coding agent(s) on Windows.

.DESCRIPTION
  Most agents read the open Agent Skills layout from .agents\skills (Codex, Cursor,
  GitHub Copilot, Gemini CLI, opencode, ...). Claude Code reads .claude\skills.

  By default each skill is installed as a directory junction pointing at this checkout,
  so `git pull` here updates every install. Junctions need no admin rights and no
  Developer Mode. Use -Copy to copy instead (e.g. to vendor the skills into a repo).

  The 6502-family skills (6502-*) come from the vendor\6502-skills submodule
  (github.com/sunsided/6502-skills) and are installed too when it is checked out:
  clone with --recurse-submodules, or run `git submodule update --init`.

  Cursor and Copilot read BOTH ~\.claude\skills and ~\.agents\skills. If you use one of
  them alongside Claude Code, installing into both can list each skill twice;
  -Claude alone covers Claude Code + Cursor + Copilot.

.EXAMPLE
  .\install.ps1 -Claude -WithAgent        # Claude Code (+ the c64-reviewer subagent)
.EXAMPLE
  .\install.ps1 -Agents                   # Codex, Cursor, Copilot, Gemini CLI, opencode
.EXAMPLE
  .\install.ps1 -Project C:\code\mydemo   # one repo: .claude\skills + .agents\skills
.EXAMPLE
  .\install.ps1 -Claude -Agents -Uninstall
#>
[CmdletBinding()]
param(
  [switch]$Claude,
  [switch]$Agents,
  [string]$Project,
  [string]$To,
  [switch]$Copy,
  [switch]$WithAgent,
  [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$Kit = $PSScriptRoot
$HomeDir = [Environment]::GetFolderPath('UserProfile')

$targets = @(); $agentDirs = @()
if ($Claude)  { $targets += Join-Path $HomeDir '.claude\skills'; $agentDirs += Join-Path $HomeDir '.claude\agents' }
if ($Agents)  { $targets += Join-Path $HomeDir '.agents\skills' }
if ($Project) {
  $p = (Resolve-Path $Project).Path
  $targets += (Join-Path $p '.claude\skills'), (Join-Path $p '.agents\skills')
  $agentDirs += Join-Path $p '.claude\agents'
}
if ($To) { $targets += $To }
if ($targets.Count -eq 0) { Get-Help $PSCommandPath -Detailed; exit 1 }

$vendor = Join-Path $Kit 'vendor\6502-skills'
$skills = @(Join-Path $Kit 'skills'; $vendor) | Where-Object { Test-Path $_ } |
  ForEach-Object { Get-ChildItem $_ -Directory } |
  Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') }
if (-not (Test-Path (Join-Path $vendor '6502-instruction-set\SKILL.md'))) {
  Write-Warning "vendor\6502-skills is not checked out; run 'git submodule update --init' for the 6502-* skills"
}

function Test-Link($path) {
  $item = Get-Item $path -Force -ErrorAction SilentlyContinue
  return $item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Install-Item($src, $dest) {
  if (Test-Link $dest) { (Get-Item $dest -Force).Delete() }
  elseif (Test-Path $dest) {
    Write-Warning "skip ${dest}: exists and is not a link from this kit (remove it first)"; return
  }
  if ($Copy -or -not (Test-Path $src -PathType Container)) {
    Copy-Item $src $dest -Recurse
  } else {
    New-Item -ItemType Junction -Path $dest -Target $src | Out-Null
  }
  Write-Host "  $dest"
}

function Remove-Item-IfOurs($dest, $ours, $theirs) {
  if (Test-Link $dest) {
    $target = (Get-Item $dest -Force).Target
    if ("$target".StartsWith($Kit)) { (Get-Item $dest -Force).Delete(); Write-Host "  removed $dest" }
    else { Write-Warning "skip ${dest}: links somewhere else" }
  } elseif (Test-Path $dest) {
    if ((Test-Path $theirs) -and ((Get-FileHash $ours).Hash -eq (Get-FileHash $theirs).Hash)) {
      Remove-Item $dest -Recurse -Force; Write-Host "  removed $dest (copy)"
    } else { Write-Warning "skip ${dest}: differs from this kit's version (edited?) - remove by hand" }
  }
}

$action = if ($Uninstall) { 'uninstall' } else { 'install' }
foreach ($t in $targets) {
  Write-Host "$action -> $t"
  if (-not $Uninstall) { New-Item -ItemType Directory -Force -Path $t | Out-Null }
  foreach ($s in $skills) {
    $dest = Join-Path $t $s.Name
    if ($Uninstall) { Remove-Item-IfOurs $dest (Join-Path $s.FullName 'SKILL.md') (Join-Path $dest 'SKILL.md') }
    else { Install-Item $s.FullName $dest }
  }
}

$agentSrc = Join-Path $Kit 'agents\claude-code\c64-reviewer.md'
if ($WithAgent -or $Uninstall) {
  foreach ($d in $agentDirs) {
    $dest = Join-Path $d 'c64-reviewer.md'
    if ($Uninstall) { Remove-Item-IfOurs $dest $agentSrc $dest }
    else { New-Item -ItemType Directory -Force -Path $d | Out-Null; Install-Item $agentSrc $dest }
  }
}

if (-not $Uninstall) {
  $c64 = Join-Path $Kit (Join-Path skills (Join-Path c64-toolchain (Join-Path scripts c64.py)))
  Write-Host "Done. Next: py -3 `"$c64`" doctor"
}
