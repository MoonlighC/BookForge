#define AppVersion GetEnv("BOOKFORGE_VERSION")
#if AppVersion == ""
  #error BOOKFORGE_VERSION must be set. Use installer\build_installer.ps1.
#endif

[Setup]
AppId={{B5E48091-189B-489A-A09E-7398428D2B02}
AppName=BookForge
AppVersion={#AppVersion}
AppVerName=BookForge {#AppVersion}
AppPublisher=Christian Rieb
DefaultDirName={localappdata}\Programs\BookForge
DefaultGroupName=BookForge
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=BookForge-Setup-{#AppVersion}
SetupIconFile=..\assets\bookforge.ico
UninstallDisplayIcon={app}\BookForge.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany=Christian Rieb
VersionInfoDescription=BookForge Windows Installer
VersionInfoProductName=BookForge
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\BookForge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BookForge"; Filename: "{app}\BookForge.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall BookForge"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BookForge"; Filename: "{app}\BookForge.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\BookForge.exe"; Description: "{cm:LaunchProgram,BookForge}"; Flags: nowait postinstall skipifsilent
