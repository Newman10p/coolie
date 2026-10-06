#ifndef AppVersion
  #define AppVersion "0.2.0-dev"
#endif

[Setup]
AppId={{7B70BE09-1D27-46C3-8B5E-2C7E970D28D3}
AppName=Coolie
AppVersion={#AppVersion}
AppPublisher=Newman10p
DefaultDirName={localappdata}\Programs\Coolie
DefaultGroupName=Coolie
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\release
OutputBaseFilename=Coolie-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Coolie.exe

[Files]
Source: "..\release\Coolie.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Coolie"; Filename: "{app}\Coolie.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Coolie"; Filename: "{app}\Coolie.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\Coolie.exe"; Description: "Launch Coolie"; Flags: postinstall nowait skipifsilent
