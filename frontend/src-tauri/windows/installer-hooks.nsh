; Older Oxo Tracker builds can leave the Python backend running when the
; in-app updater exits the desktop shell. Its loaded DLL/PYD files then remain
; locked and NSIS cannot replace oxo-backend-lib. Stop that orphan immediately
; before file extraction so upgrades from those builds can recover themselves.
!macro NSIS_HOOK_PREINSTALL
  DetailPrint "Stopping the Oxo Tracker background service..."
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM "oxo-backend.exe"'
  Sleep 300
!macroend
