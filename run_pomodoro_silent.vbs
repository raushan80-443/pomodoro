' Silent Background Launcher for Pomodoro on Windows
' Launches run_pomodoro.bat with hidden console window (window style 0)
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
batPath = scriptDir & "\run_pomodoro.bat"

WshShell.Run "cmd /c """ & batPath & """", 0, False
Set WshShell = Nothing
Set FSO = Nothing
