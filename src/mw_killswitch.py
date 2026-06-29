import os
import sys
import tkinter as tk
import subprocess
import ctypes

hosts = r"C:\Windows\System32\drivers\etc\hosts"
line = "127.0.0.1 www.motivewave.com"
marker = "# MW_BLOCK"

def check():
    try:
        with open(hosts, 'r') as f:
            return line in f.read()
    except:
        return False

def toggle():
    blocked = check()
    try:
        with open(hosts, 'r') as f:
            data = f.readlines()
        
        with open(hosts, 'w') as f:
            for d in data:
                if marker not in d and line not in d:
                    f.write(d)
            if not blocked:
                f.write(f"\n{line} {marker}\n")
        
        subprocess.run(["ipconfig", "/flushdns"], creationflags=subprocess.CREATE_NO_WINDOW)
        update()
    except Exception as e:
        pass # skip error handling

def get_pos(e):
    root.xwin = root.winfo_x() - e.x_root
    root.ywin = root.winfo_y() - e.y_root

def move_app(e):
    root.geometry(f"+{e.x_root + root.xwin}+{e.y_root + root.ywin}")

def update():
    blocked = check()
    if blocked:
        status_var.set("STATUS: BLOCKED")
        btn.config(text="RESTORE CONNECTION", bg="#1a1a1a")
        desc_var.set("MotiveWave heartbeat is currently blocked.\nThe license is released for your home PC.")
    else:
        status_var.set("STATUS: ACTIVE")
        btn.config(text="DROP CONNECTION", bg="#1a1a1a")
        desc_var.set("MotiveWave heartbeat is active.\nDrop connection to free up the license.")

root = tk.Tk()
root.geometry("400x240")
root.configure(bg="#0a0a0a")
root.overrideredirect(True) # hide standard title bar

# hack to force borderless window into taskbar
root.update_idletasks()
hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
style = style & ~0x00000080 | 0x00040000
ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
root.withdraw()
root.deiconify()

# custom drag bar
top = tk.Frame(root, bg="#0a0a0a", height=30)
top.pack(fill="x")
top.bind("<Button-1>", get_pos)
top.bind("<B1-Motion>", move_app)

close_btn = tk.Button(top, text="✕", bg="#0a0a0a", fg="#666666", bd=0, 
                      activebackground="#ff3333", activeforeground="white", 
                      command=root.destroy, font=("Arial", 12))
close_btn.pack(side="right", padx=10)

title_lbl = tk.Label(top, text="MW Session Blocker", bg="#0a0a0a", fg="#444444", font=("Arial", 8))
title_lbl.pack(side="left", padx=12, pady=5)
title_lbl.bind("<Button-1>", get_pos)
title_lbl.bind("<B1-Motion>", move_app)

# ui elements
status_var = tk.StringVar()
status_lbl = tk.Label(root, textvariable=status_var, font=("Segoe UI", 16, "bold"), bg="#0a0a0a", fg="#ffffff")
status_lbl.pack(pady=(25, 15))

btn = tk.Button(root, text="DROP CONNECTION", font=("Segoe UI", 10, "bold"), 
                bg="#1a1a1a", fg="#ffffff", activebackground="#2a2a2a", activeforeground="#ffffff", 
                bd=1, relief="solid", cursor="hand2", width=30, height=2, command=toggle)
btn.pack(pady=10)

desc_var = tk.StringVar()
desc_lbl = tk.Label(root, textvariable=desc_var, font=("Segoe UI", 9), bg="#0a0a0a", fg="#777777")
desc_lbl.pack(pady=10)

update()
root.mainloop()
