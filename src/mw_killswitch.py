import os
import sys
import tkinter as tk
import subprocess
import ctypes
import threading
import math

hosts = r"C:\Windows\System32\drivers\etc\hosts"
line = "127.0.0.1 www.motivewave.com"
marker = "# MW_BLOCK"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("400x260")
        self.configure(bg="#0a0a0a")
        self.overrideredirect(True)
        
        self.is_loading = False
        self.angle = 0
        
        # taskbar hack
        self.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x00000080 | 0x00040000
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        self.withdraw()
        self.deiconify()

        # custom drag bar
        top = tk.Frame(self, bg="#0a0a0a", height=30)
        top.pack(fill="x")
        top.bind("<Button-1>", self.get_pos)
        top.bind("<B1-Motion>", self.move_app)

        close_btn = tk.Button(top, text="✕", bg="#0a0a0a", fg="#666666", bd=0, 
                              activebackground="#ff3333", activeforeground="white", 
                              command=self.destroy, font=("Arial", 12))
        close_btn.pack(side="right", padx=10)

        title_lbl = tk.Label(top, text="GhostWave", bg="#0a0a0a", fg="#444444", font=("Arial", 8))
        title_lbl.pack(side="left", padx=12, pady=5)
        title_lbl.bind("<Button-1>", self.get_pos)
        title_lbl.bind("<B1-Motion>", self.move_app)

        # Status Label
        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 16, "bold"), bg="#0a0a0a", fg="#ffffff")
        self.status_lbl.pack(pady=(15, 5))

        # Canvas for real loading spinner & glowing dot
        self.canvas = tk.Canvas(self, width=200, height=40, bg="#0a0a0a", bd=0, highlightthickness=0)
        self.canvas.pack()

        # Button
        self.btn = tk.Button(self, text="...", font=("Segoe UI", 10, "bold"), 
                        bg="#1a1a1a", fg="#ffffff", activebackground="#2a2a2a", activeforeground="#ffffff", 
                        bd=1, relief="solid", cursor="hand2", width=30, height=2, command=self.start_toggle)
        self.btn.pack(pady=10)

        self.desc_var = tk.StringVar()
        self.desc_lbl = tk.Label(self, textvariable=self.desc_var, font=("Segoe UI", 9), bg="#0a0a0a", fg="#777777")
        self.desc_lbl.pack(pady=5)
        
        self.update_ui()

    def get_pos(self, e):
        self.xwin = self.winfo_x() - e.x_root
        self.ywin = self.winfo_y() - e.y_root

    def move_app(self, e):
        self.geometry(f"+{e.x_root + self.xwin}+{e.y_root + self.ywin}")

    def check(self):
        try:
            with open(hosts, 'r') as f:
                return line in f.read()
        except:
            return False

    def update_ui(self):
        blocked = self.check()
        self.canvas.delete("all")
        if blocked:
            self.status_var.set("STATUS: BLOCKED")
            self.btn.config(text="RESTORE CONNECTION", bg="#1a1a1a", state=tk.NORMAL)
            self.desc_var.set("MotiveWave heartbeat is currently blocked.\nThe license is released for your home PC.")
            
            self.glow_step = 0
            self.animate_glow()
        else:
            self.status_var.set("STATUS: ACTIVE")
            self.btn.config(text="DROP CONNECTION", bg="#1a1a1a", state=tk.NORMAL)
            self.desc_var.set("MotiveWave heartbeat is active.\nDrop connection to free up the license.")
            
    def animate_glow(self):
        if not self.check() or self.is_loading:
            return
            
        self.canvas.delete("glow")
        
        # Smooth appearance: scale up over 15 frames
        scale = min(1.0, self.glow_step / 15.0)
        
        # Continuous subtle pulse after appearing
        if scale >= 1.0:
            pulse = math.sin((self.glow_step - 15) * 0.1) * 0.15 + 0.85
        else:
            pulse = scale

        cx, cy = 60, 20
        
        # Layered circles to create a true gradient glow effect
        colors = ["#1a1a1a", "#222222", "#333333", "#555555", "#aaaaaa", "#ffffff"]
        max_r = 14 * pulse
        
        for i, color in enumerate(colors):
            r = max_r * (1 - i/len(colors))
            if r > 0:
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="", tags="glow")
                
        # Fade text in smoothly
        if scale > 0.3:
            c_val = int(255 * min(1.0, (scale - 0.3) * 1.5))
            hex_c = f"#{c_val:02x}{c_val:02x}{c_val:02x}"
            self.canvas.create_text(110, 20, text="LICENSE FREE", fill=hex_c, font=("Segoe UI", 8, "bold"), tags="glow")
            
        self.glow_step += 1
        self.after(30, self.animate_glow)
            
    def start_toggle(self):
        if self.is_loading: return
        self.is_loading = True
        self.btn.config(state=tk.DISABLED, text="WORKING...")
        self.canvas.delete("all")
        
        # Spawn thread for the actual file/network operations so UI doesn't freeze
        threading.Thread(target=self.do_toggle, daemon=True).start()
        self.animate_loading()

    def do_toggle(self):
        blocked = self.check()
        try:
            with open(hosts, 'r') as f:
                data = f.readlines()
            
            with open(hosts, 'w') as f:
                for d in data:
                    if marker not in d and line not in d:
                        f.write(d)
                if not blocked:
                    f.write(f"\n{line} {marker}\n")
            
            # The real loading work: flushing Windows DNS cache to ensure immediate disconnect
            subprocess.run(["ipconfig", "/flushdns"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
            
        self.is_loading = False

    def animate_loading(self):
        if not self.is_loading:
            self.update_ui()
            return
            
        self.canvas.delete("spinner")
        self.angle = (self.angle + 25) % 360
        self.canvas.create_arc(85, 5, 115, 35, start=self.angle, extent=270, outline="#ffffff", width=2, style=tk.ARC, tags="spinner")
        
        # 30ms frame loop
        self.after(30, self.animate_loading)

if __name__ == "__main__":
    app = App()
    app.mainloop()
