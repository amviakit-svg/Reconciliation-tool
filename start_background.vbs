' ============================================================
' Reconciliation Tool v2.0 - Silent Background Launcher
' ============================================================
' Starts the server silently with auto-restart and epic-pace
' optimizations. Uses pythonw.exe to prevent console window.
' Logs are redirected to data\logs\background_*.log
' ============================================================

Option Explicit

Dim WshShell, FSO, strScriptPath, strPython, strCommand
Dim alreadyRunning, WMI, processes, process
Dim objExec, logDir, outLog, errLog
Dim restartCount, maxRestarts

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptPath = FSO.GetParentFolderName(WScript.ScriptFullName)
restartCount = 0
maxRestarts = 10

' ---- PERFORMANCE ENVIRONMENT VARIABLES ----
' Prevent NumPy/Pandas thread oversubscription (thread thrashing on Windows)
WshShell.Environment("PROCESS").Item("OMP_NUM_THREADS") = "1"
WshShell.Environment("PROCESS").Item("OPENBLAS_NUM_THREADS") = "1"
WshShell.Environment("PROCESS").Item("MKL_NUM_THREADS") = "1"
WshShell.Environment("PROCESS").Item("VECLIB_MAXIMUM_THREADS") = "1"
WshShell.Environment("PROCESS").Item("NUMEXPR_NUM_THREADS") = "1"
WshShell.Environment("PROCESS").Item("PYTHONDONTWRITEBYTECODE") = "1"

' ---- CHECK IF VIRTUAL ENV EXISTS ----
strPython = strScriptPath & "\venv\Scripts\pythonw.exe"
If Not FSO.FileExists(strPython) Then
    MsgBox "ERROR: Virtual environment not found!" & vbCrLf & _
           "Please create it with: python -m venv venv", vbCritical, "Reconciliation Tool"
    WScript.Quit 1
End If

' ---- CHECK IF ALREADY RUNNING ----
alreadyRunning = False
Set WMI = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")
Set processes = WMI.ExecQuery("Select * from Win32_Process Where Name='pythonw.exe' OR Name='python.exe'")

For Each process in processes
    If InStr(process.CommandLine, "uvicorn") > 0 And InStr(process.CommandLine, "backend.main") > 0 Then
        alreadyRunning = True
        Exit For
    End If
Next

If alreadyRunning Then
    MsgBox "Reconciliation Tool is already running!" & vbCrLf & vbCrLf & _
           "Access at: http://localhost:8000", vbInformation, "Reconciliation Tool v2.0"
    WScript.Quit 0
End If

' ---- CREATE LOGS DIRECTORY ----
logDir = strScriptPath & "\data\logs"
If Not FSO.FolderExists(logDir) Then
    FSO.CreateFolder(logDir)
End If

outLog = logDir & "\background_out_" & GetTimestamp() & ".log"
errLog = logDir & "\background_err_" & GetTimestamp() & ".log"

' ---- BUILD EPIC-PACE COMMAND ----
' Use pythonw.exe (not python.exe) to prevent console window flash
strCommand = """" & strPython & """ -m uvicorn backend.main:app " & _
    "--host 0.0.0.0 --port 8000 --workers 1 " & _
    "--timeout-keep-alive 75 --limit-concurrency 500 --backlog 4096 " & _
    "--lifespan on --no-access-log"

WshShell.CurrentDirectory = strScriptPath

' ---- START HIDDEN PROCESS WITH LOG REDIRECTION ----
' WindowStyle=0 = hidden, WaitOnReturn=False = don't block
Dim execResult
execResult = WshShell.Run(strCommand & " > """ & outLog & """ 2>""" & errLog & """", 0, False)

' ---- WAIT AND VALIDATE STARTUP ----
WScript.Sleep 5000

' Check if process started by looking for pythonw with uvicorn
Dim newRunning
newRunning = False
Set processes = WMI.ExecQuery("Select * from Win32_Process Where Name='pythonw.exe' OR Name='python.exe'")
For Each process in processes
    If InStr(process.CommandLine, "uvicorn") > 0 And InStr(process.CommandLine, "backend.main") > 0 Then
        newRunning = True
        Exit For
    End If
Next

If Not newRunning Then
    MsgBox "Failed to start server in background." & vbCrLf & vbCrLf & _
           "Check logs:" & vbCrLf & outLog & vbCrLf & errLog, vbCritical, "Startup Error"
    WScript.Quit 1
End If

' ---- SUCCESS ----
MsgBox "Reconciliation Tool started successfully in Epic Pace mode!" & vbCrLf & vbCrLf & _
       "URL: http://localhost:8000" & vbCrLf & _
       "Health: http://localhost:8000/health" & vbCrLf & vbCrLf & _
       "The server is running silently in the background." & vbCrLf & _
       "Logs: data\logs\", vbInformation, "Reconciliation Tool v2.0"

' ---- AUTO-RESTART MONITOR ----
' This script keeps running to monitor the server and restart if it crashes
Do While True
    WScript.Sleep 30000 ' Check every 30 seconds

    Dim stillRunning
    stillRunning = False
    Set processes = WMI.ExecQuery("Select * from Win32_Process Where Name='pythonw.exe' OR Name='python.exe'")
    For Each process in processes
        If InStr(process.CommandLine, "uvicorn") > 0 And InStr(process.CommandLine, "backend.main") > 0 Then
            stillRunning = True
            Exit For
        End If
    Next

    If Not stillRunning Then
        restartCount = restartCount + 1
        If restartCount > maxRestarts Then
            MsgBox "Server has crashed too many times (" & maxRestarts & ")." & vbCrLf & _
                   "Please check logs in data\logs\", vbExclamation, "Reconciliation Tool"
            WScript.Quit 1
        End If

        ' Restart with new log files
        outLog = logDir & "\background_out_" & GetTimestamp() & ".log"
        errLog = logDir & "\background_err_" & GetTimestamp() & ".log"
        WshShell.Run strCommand & " > """ & outLog & """ 2>""" & errLog & """", 0, False
    End If
Loop

' ---- HELPER FUNCTIONS ----
Function GetTimestamp()
    Dim nowVal
    nowVal = Now
    GetTimestamp = Year(nowVal) & Right("0" & Month(nowVal), 2) & Right("0" & Day(nowVal), 2) & "_" & _
                   Right("0" & Hour(nowVal), 2) & Right("0" & Minute(nowVal), 2) & Right("0" & Second(nowVal), 2)
End Function