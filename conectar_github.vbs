' Conectar ao GitHub de forma acessivel (v2, sem bug de aspas).
' Mostra UMA caixa para colar o token, conecta e avisa o resultado.
Option Explicit

Dim shell, gh, token, oExec, errText, outText, code
Set shell = CreateObject("WScript.Shell")
gh = Chr(34) & "C:\Program Files\GitHub CLI\gh.exe" & Chr(34)

' 1) Caixa de dialogo para colar o token (acessivel ao leitor de tela)
token = InputBox( _
  "Cole aqui o token do GitHub (Ctrl+V) e clique em OK.", _
  "Conectar ao GitHub - Poker Acessivel")

If Trim(token) = "" Then
  MsgBox "Nenhum token foi colado. Gere o token no site e rode este arquivo de novo.", _
         vbExclamation, "Poker Acessivel"
  WScript.Quit
End If

' 2) Roda o gh e escreve o token diretamente na entrada dele (sem arquivo, sem cmd)
On Error Resume Next
Set oExec = shell.Exec(gh & " auth login --hostname github.com --git-protocol https --with-token")
If Err.Number <> 0 Then
  MsgBox "Nao encontrei o programa do GitHub (gh). Erro: " & Err.Description, vbExclamation, "Poker Acessivel"
  WScript.Quit
End If
On Error GoTo 0

oExec.StdIn.Write Trim(token) & vbLf
oExec.StdIn.Close

' espera terminar
Do While oExec.Status = 0
  WScript.Sleep 100
Loop

errText = ""
outText = ""
On Error Resume Next
errText = oExec.StdErr.ReadAll()
outText = oExec.StdOut.ReadAll()
On Error GoTo 0
code = oExec.ExitCode

' 3) Resultado
If code = 0 Then
  shell.Run gh & " auth setup-git", 0, True
  MsgBox "Conectado ao GitHub com sucesso!" & vbCrLf & vbCrLf & _
         "Volte para a conversa e escreva: conectado", vbInformation, "Poker Acessivel"
Else
  MsgBox "Nao consegui conectar." & vbCrLf & vbCrLf & _
         "Motivo tecnico (por favor me mande este texto):" & vbCrLf & _
         errText & outText, vbExclamation, "Poker Acessivel"
End If
