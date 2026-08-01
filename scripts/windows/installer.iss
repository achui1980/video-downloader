#define MyAppName "VideoDownloader"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppDir "..\..\dist\VideoDownloader"

[Setup]
AppId={{8F1B6D2A-9C42-4E6E-9F3D-2A1B0C7E5A90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=VideoDownloader
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\setup
OutputBaseFilename=VideoDownloader-{#MyAppVersion}-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#MyAppDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\VideoDownloader.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\VideoDownloader.exe"

[Run]
Filename: "{app}\VideoDownloader.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
