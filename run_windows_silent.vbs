Set shell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonwPath = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python311\pythonw.exe"
shell.CurrentDirectory = scriptDir
shell.Run """" & pythonwPath & """ """ & scriptDir & "\run_windows.pyw""", 0, False
