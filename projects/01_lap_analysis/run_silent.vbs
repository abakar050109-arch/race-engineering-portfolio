' Silent launcher for the lap analysis.
'
' Double-click this file: no console window appears, the analysis runs in the
' background, and the results folder opens by itself.
'
' This file only starts run_analysis.bat in silent mode, so the Python lookup
' is exactly the same as when the batch file is started by hand.
'
' If the analysis fails, a message box appears with the exit code.

Option Explicit

Dim fso, shell, base, rc

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

base = fso.GetParentFolderName(WScript.ScriptFullName)

' 0 = hidden window, True = wait until the batch file finishes
rc = shell.Run("cmd /c """ & base & "\run_analysis.bat"" silent", 0, True)

If rc <> 0 Then
    MsgBox "Analysis failed (exit code " & rc & ")." & vbCrLf & vbCrLf & _
           "Double-click run_analysis.bat to see the full error message.", _
           16, "Lap analysis"
End If
