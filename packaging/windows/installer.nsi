; AI AGENT CUT — Windows installer (NSIS). Per-user install, no admin rights needed.
Unicode true
!define APP "AI AGENT CUT"
!ifndef VERSION
!define VERSION "2.0.0"
!endif
Name "${APP}"
OutFile "${OUTDIR}\AIAgentCut-Setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\AIAgentCut"
RequestExecutionLevel user
SetCompressor /SOLID lzma
Icon "app.ico"
UninstallIcon "app.ico"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP}"
VIAddVersionKey "FileDescription" "Long video in. Viral clips out."
VIAddVersionKey "FileVersion" "${VERSION}"
!include "MUI2.nsh"
!define MUI_ICON "app.ico"
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!define MUI_FINISHPAGE_RUN_TEXT "Open AI AGENT CUT"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${STAGE}\*.*"
  CreateShortcut "$DESKTOP\AI AGENT CUT.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\launcher.pyw"' "$INSTDIR\app.ico"
  CreateDirectory "$SMPROGRAMS\AI AGENT CUT"
  CreateShortcut "$SMPROGRAMS\AI AGENT CUT\AI AGENT CUT.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\launcher.pyw"' "$INSTDIR\app.ico"
  CreateShortcut "$SMPROGRAMS\AI AGENT CUT\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAgentCut" "DisplayName" "${APP}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAgentCut" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAgentCut" "DisplayIcon" "$INSTDIR\app.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAgentCut" "DisplayVersion" "${VERSION}"
SectionEnd
Section "Uninstall"
  Delete "$DESKTOP\AI AGENT CUT.lnk"
  RMDir /r "$SMPROGRAMS\AI AGENT CUT"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAgentCut"
SectionEnd
Function LaunchApp
  Exec '"$INSTDIR\python\pythonw.exe" "$INSTDIR\launcher.pyw"'
FunctionEnd
