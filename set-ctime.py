#!C:\Users\Jaga\AppData\Local\Programs\Python\Python38-32\python.exe

from win32_setctime import setctime
import sys

if len(sys.argv) < 3:
    print("Not enough arguments given. Usage: set-ctime.py file date(e.g 1561675987.509")
else:
    file_path = sys.argv[1]
    date = sys.argv[2]

    setctime(file_path, float(date))
