#ifndef AppVersion
  #define AppVersion "0.7.0"
#endif
#ifndef PayloadDir
  #error PayloadDir required
#endif
#ifndef OutputPath
  #error OutputPath required
#endif
[Setup]
AppId={{0748246D-1B81-4CDB-A9BA-00D241D20B51}
AppName=WorkBuddy 桌宠
AppVersion={#AppVersion}
AppPublisher=WorkBuddy Desktop Pet
AppPublisherURL=https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet
DefaultDirName={localappdata}\Programs\WorkBuddyDesktopPet
DefaultGroupName=WorkBuddy 桌宠
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19045
OutputDir={#OutputPath}
OutputBaseFilename=workbuddy-desktop-pet-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
DisableWelcomePage=no
UninstallDisplayIcon={app}\WorkBuddyDesktopPet.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
Name: "connect"; Description: "连接 WorkBuddy，安装本地任务状态插件"; GroupDescription: "首次使用授权（已有设置将保留）："
Name: "connect\balance"; Description: "允许查询账户剩余积分"
Name: "connect\checkin"; Description: "允许查询签到；只有点击签到才领取"
Name: "startup"; Description: "登录 Windows 后启动桌宠"; GroupDescription: "启动选项："; Flags: unchecked
[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\WorkBuddy 桌宠"; Filename: "{app}\WorkBuddyDesktopPet.exe"
Name: "{autodesktop}\WorkBuddy 桌宠"; Filename: "{app}\WorkBuddyDesktopPet.exe"; Tasks: desktopicon
[Registry]
Root: HKCU; Subkey: "Software\WorkBuddyDesktopPet\Installer"; ValueType: string; ValueName: "DataRoot"; ValueData: "{code:GetPetRoot}"; Flags: uninsdeletevalue uninsdeletekeyifempty
[Run]
Filename: "{app}\WorkBuddyDesktopPet.exe"; Parameters: "--root ""{code:GetPetRoot}"""; Description: "启动 WorkBuddy 桌宠"; Flags: nowait postinstall skipifsilent
[UninstallRun]
Filename: "{app}\WorkBuddyDesktopPet.exe"; Parameters: "--root ""{code:GetPetRoot}"" --setup-remove"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveOwnedIntegration"
[Code]
function GetPetRoot(Param: String): String;
begin
  Result := ExpandConstant('{localappdata}\WorkBuddyDesktopPet');
  if IsUninstaller then
    RegQueryStringValue(HKCU, 'Software\WorkBuddyDesktopPet\Installer', 'DataRoot', Result)
  else Result := ExpandConstant('{param:PETROOT|' + Result + '}');
end;
function SelectedFlag(Name: String): String;
begin
  if WizardIsTaskSelected(Name) then Result := '1' else Result := '0';
end;
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpSelectTasks) and FileExists(GetPetRoot('') + '\settings.json');
end;
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption := '将桌宠安装到当前用户目录，集中完成连接与积分功能授权。' + #13#10 + #13#10 +
    '连接票据仅在本机使用，不上传、不写入日志。签到必须由你点击才领取。已有用户更新将保留角色与授权设置。WorkBuddy 登录及任务审批仍由你在 WorkBuddy 中完成。';
end;
procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer; Args: String;
begin
  if CurStep = ssPostInstall then begin
    Args := '--root "' + GetPetRoot('') + '" --workbuddy-home "' +
      ExpandConstant('{param:WORKBUDDYHOME|{%USERPROFILE}\.workbuddy}') + '" --setup-apply' +
      ' --setup-connect=' + SelectedFlag('connect') + ' --setup-balance=' + SelectedFlag('connect\balance') +
      ' --setup-checkin=' + SelectedFlag('connect\checkin') + ' --setup-startup=' + SelectedFlag('startup');
    if ExpandConstant('{param:WORKBUDDYEXE|}') <> '' then Args := Args + ' --setup-workbuddy-exe "' + ExpandConstant('{param:WORKBUDDYEXE|}') + '"';
    if not Exec(ExpandConstant('{app}\WorkBuddyDesktopPet.exe'), Args, '', SW_HIDE, ewWaitUntilTerminated, Code) then Code := 1;
    if Code <> 0 then
      SuppressibleMsgBox('程序已安装，但 WorkBuddy 接入尚未完成。请启动并登录 WorkBuddy，再在桌宠设置中点击连接。已有授权未被覆盖。', mbInformation, MB_OK, IDOK);
  end;
end;
