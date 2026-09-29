' silent-run.vbs: Executes any command or script completely invisible (0 window flash).
' Uses Windows Script Host GUI subsystem to eliminate console window creation.
Dim oShell, cmd, i
Set oShell = CreateObject("WScript.Shell")
If WScript.Arguments.Count > 0 Then
    cmd = ""
    For i = 0 To WScript.Arguments.Count - 1
        arg = WScript.Arguments(i)
        If InStr(arg, " ") > 0 And Left(arg, 1) <> """" Then
            cmd = cmd & " """ & arg & """"
        Else
            cmd = cmd & " " & arg
        End If
    Next
    oShell.Run Trim(cmd), 0, False
End If
