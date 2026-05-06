@echo off
REM Run main.py and capture output to run_main_output.txt
"C:\Users\Code Farm\Desktop\scripts\BLOG_POST\ENVIRONMENT\Scripts\python.exe" "C:\Users\Code Farm\Desktop\scripts\BLOG_POST\main.py" "C:\Users\Code Farm\Desktop\scripts\BLOG_POST\input.csv" > "C:\Users\Code Farm\Desktop\scripts\BLOG_POST\run_main_output.txt" 2>&1
type "C:\Users\Code Farm\Desktop\scripts\BLOG_POST\run_main_output.txt"
pause
