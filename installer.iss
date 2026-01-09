; School Bell Professional Installer
; Designed for Windows 11 Compatibility

#define MyAppName "School Bell Professional"
#define MyAppVersion "1.5"
#define MyAppPublisher "TeaTalk"
#define MyAppExeName "SchoolBell.exe"
#define MyOutputDir "dist\SchoolBell"

[Setup]
AppId={{7B8B1A2C-5F9D-4E3E-A5B2-D4C5E6F7A8B9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Customize the output filename
OutputBaseFilename=SchoolBell_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Launch School Bell on system startup"; GroupDescription: "Auto-Start:"; Flags: unchecked

[Files]
; Copy the ENTIRE folder from dist\SchoolBell
Source: "{#MyOutputDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; The Startup Folder shortcut
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--startup"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
