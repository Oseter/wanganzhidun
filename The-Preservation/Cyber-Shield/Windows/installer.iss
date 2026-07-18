; 网安智盾 安装包脚本 (Inno Setup 6)
; CI 在 Windows  runner 上用 iscc 编译，产出 WangAnZhiDun-Setup.exe
#define MyAppName "网安智盾 WangAnZhiDun"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "民用武器体系"
#define MyAppURL "https://github.com/Oseter/wanganzhidun"
#define MyExe "WangAnZhiDun.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
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

[Languages]
; 注：本环境 Inno Setup 未自带中文语言包。应用内 UI 为中文，
; 安装向导暂用英文（Default.isl）。如需中文安装界面，把官方
; ChineseSimplified.isl 放入 Languages\ 后改回对应 MessagesFile 即可。
Name: "English"; MessagesFile: "compiler:Default.isl"

[Files]
; PyInstaller 产出 + 配置文件，一起装到程序目录
Source: "dist\{#MyExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "附加任务:"

[Run]
Filename: "{app}\{#MyExe}"; Description: "安装完成后启动网安智盾"; Flags: nowait postinstall skipifsilent
