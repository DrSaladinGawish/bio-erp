Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\ERP System\BIO_ERP\app\organs\incentivehouse_organ"
WshShell.Run "python incentivehouse_server.py", 0, False
