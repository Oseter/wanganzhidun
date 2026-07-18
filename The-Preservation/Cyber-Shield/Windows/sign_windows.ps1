# 网安智盾 Windows 版 — Authenticode 代码签名脚本
#
# 为什么需要它：未签名的 PyInstaller exe 会被 SmartScreen / Microsoft Defender /
# Edge 下载拦截（红框「Windows 已保护你的电脑」）。这是「去威胁」唯一可靠的手段。
# 光改打包参数（关 UPX / 加 manifest / 版本信息）只能降低启发式误报，无法消除
# 对未签名程序的信任警告。
#
# 前置条件：
#   1. 一张 Authenticode 代码签名证书（.pfx）。普通 DV 证书需积累 SmartScreen
#      信誉（用户下载量起来后才不弹）；EV 证书自带即时 SmartScreen 信誉，最省心。
#   2. signtool.exe（Windows SDK / Visual Studio 自带）。
#
# 用法（本地）：
#   $env:PFX_PATH = "D:\cert.pfx"; $env:PFX_PWD = "证书密码"
#   .\sign_windows.ps1
#
# 用法（CI，从 secret 注入 base64）：
#   把 pfx 转 base64：  [Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx"))
#   在仓库 Secrets 里存为 WIN_CERT_PFX（base64）与 WIN_CERT_PWD（密码），
#   build.yml 的签名步骤会自动解码并调用本脚本。
#
# 参数：
#   -Target  待签名文件（默认 onedir 产物）

param(
  [string]$Target = "dist\WangAnZhiDun\WangAnZhiDun.exe"
)

# 1) 定位 signtool
$signtool = Get-Command signtool -ErrorAction SilentlyContinue
if (-not $signtool) {
  $cands = @(
    "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe",
    "C:\Program Files\Windows Kits\10\bin\*\x64\signtool.exe"
  )
  foreach ($c in $cands) {
    $s = Resolve-Path $c -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($s) { $signtool = $s.Path; break }
  }
}
if (-not $signtool) {
  Write-Error "signtool 未找到，请安装 Windows SDK 或 Visual Studio 后重试。"
  exit 1
}

# 2) 解析证书：优先 base64（CI），其次本地文件（本地）
$pfxFile = $null
if ($env:PFX_B64) {
  $pfxFile = Join-Path $env:TEMP "wangzhidun_sign.pfx"
  [IO.File]::WriteAllBytes($pfxFile, [Convert]::FromBase64String($env:PFX_B64))
  Write-Host "已从 PFX_B64 解码证书到 $pfxFile"
} elseif ($env:PFX_PATH -and (Test-Path $env:PFX_PATH)) {
  $pfxFile = $env:PFX_PATH
} else {
  Write-Error "未提供证书：请设置 PFX_B64（CI）或 PFX_PATH（本地）。"
  exit 1
}

$pwd = $env:PFX_PWD
if (-not $pwd) {
  Write-Error "未提供证书密码：请设置 PFX_PWD。"
  exit 1
}

if (-not (Test-Path $Target)) {
  Write-Error "待签名文件不存在：$Target"
  exit 1
}

# 3) 签名 + RFC3161 时间戳（时间戳确保证书过期后签名仍有效）
& $signtool sign /fd SHA256 /td SHA256 `
  /tr http://timestamp.digicert.com `
  /f "$pfxFile" /p "$pwd" "$Target"
if ($LASTEXITCODE -ne 0) {
  Write-Error "签名失败（signtool 退出码 $LASTEXITCODE）。"
  exit 1
}

Write-Host "已签名：$Target"
# 本地 base64 解码产生的临时 pfx 用完即删
if ($env:PFX_B64 -and $pfxFile) {
  Remove-Item $pfxFile -Force -ErrorAction SilentlyContinue
}
