; 网安智盾 安装包脚本 (Inno Setup 6)
; CI 在 Windows runner 上用 iscc 编译，产出 WangAnZhiDun-Setup.exe
#define MyAppName "网安智盾 WangAnZhiDun"
#define MyAppVersion "1.5.0-beta"
#define MyAppNumVersion "1.5.0.0"
#define MyAppPublisher "民用武器体系"
#define MyAppURL "https://github.com/Oseter/wanganzhidun"
#define MyExe "WangAnZhiDun.exe"
#define MyExeDir "WangAnZhiDun"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
; 文件版本信息（详情页展示）
VersionInfoVersion={#MyAppNumVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=网安智盾 · 存护命途取证与反制工具（v1.5 测试版）
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppNumVersion}
VersionInfoCopyright=Copyright (C) 民用武器体系
DefaultDirName={localappdata}\WangAnZhiDun
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=WangAnZhiDun-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 装到用户目录，免管理员/UAC，普通用户零门槛安装
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyExe}
; 品牌资源（盾牌图标 / 向导图，由 tools/gen_installer_art.py 生成）
SetupIconFile=resources\icon.ico
WizardImageFile=installer\wizard.bmp
WizardSmallImageFile=installer\wizard-small.bmp
; 安装前功能说明 + 合法使用声明（红线）
InfoBeforeFile=installer\infobefore.txt
LicenseFile=installer\license.txt
; 其它体验
AlwaysShowComponentsList=no
DisableProgramGroupPage=auto
SetupLogging=yes

[Files]
; PyInstaller 产出（onedir：dist\WangAnZhiDun\ 目录）+ 配置文件，一起装到程序目录
Source: "dist\{#MyExeDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "附加任务:"
Name: "autostart"; Description: "开机自动启动（最小化到托盘）(&R)"; GroupDescription: "附加任务:"

[Registry]
; 开机自启：仅当选中 autostart 任务时写入，卸载时清理
Root: "HKCU"; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "WangAnZhiDun"; \
  ValueData: """{app}\{#MyExe}"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyExe}"; Description: "安装完成后启动网安智盾"; Flags: nowait postinstall skipifsilent
