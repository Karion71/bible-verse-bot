' 창을 띄우지 않고 봇을 백그라운드로 실행한다.
Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonw = "C:\Users\kario\AppData\Local\Programs\Python\Python311\pythonw.exe"
cmd = """" & pythonw & """ """ & scriptDir & "\bot.py"""
WshShell.CurrentDirectory = scriptDir
WshShell.Run cmd, 0, False
