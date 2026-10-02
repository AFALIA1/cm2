; Inno Setup script for the Windows installer (built by packaging/build_windows.ps1).
; Installs dist\cm2\ (app + bundled ffmpeg/ffprobe). A wizard checkbox picks whether the
; install folder is added to the system PATH automatically or left for the user to add.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7C2B6C1E-4C55-4E0B-9A3B-2D7E0C2A9F11}
AppName=cm2
AppVersion={#AppVersion}
DefaultDirName={autopf}\cm2
DefaultGroupName=cm2
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ChangesEnvironment=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=cm2-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=cm2
CloseApplications=yes

[Tasks]
Name: addtopath; Description: "Add cm2 to the PATH environment variable automatically (recommended)"; \
    GroupDescription: "Environment variable:"

; Upgrading over an older version: clear the old bundle first so libraries the new
; version dropped don't linger in _internal (same AppId = same folder, in place).
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\cm2\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\cm2"; Filename: "{cmd}"; Parameters: "/k ""{app}\cm2.exe"""; WorkingDir: "{userdocs}"
Name: "{group}\Uninstall cm2"; Filename: "{uninstallexe}"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; \
    Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{cmd}"; Parameters: "/k ""{app}\cm2.exe"""; Description: "Open cm2 now"; \
    Flags: postinstall nowait skipifsilent

[Code]
const EnvKey = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';

function NeedsAddPath(Dir: string): Boolean;
var
  Paths: string;
begin
  if not RegQueryStringValue(HKLM, EnvKey, 'Path', Paths) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Paths) + ';') = 0;
end;

// Unticked PATH box: tell the user how to set it themselves on the last page.
procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpFinished) and not WizardIsTaskSelected('addtopath') then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 +
      'cm2 was NOT added to PATH. Run it as:' + #13#10 +
      '  "' + ExpandConstant('{app}') + '\cm2.exe"' + #13#10#13#10 +
      'To add it yourself: Start > "Edit the system environment variables" > ' +
      'Environment Variables > Path > Edit > New, and paste:' + #13#10 +
      '  ' + ExpandConstant('{app}');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Paths, Dir: string;
  P: Integer;
begin
  if CurUninstallStep <> usPostUninstall then exit;
  if not RegQueryStringValue(HKLM, EnvKey, 'Path', Paths) then exit;
  Dir := ExpandConstant('{app}');
  P := Pos(';' + Uppercase(Dir), Uppercase(Paths));
  if P > 0 then
  begin
    Delete(Paths, P, Length(Dir) + 1);
    RegWriteExpandStringValue(HKLM, EnvKey, 'Path', Paths);
  end;
end;
