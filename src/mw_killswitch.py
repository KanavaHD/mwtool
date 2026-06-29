import os
import sys
import tkinter as tk
import subprocess
import ctypes
import threading
import math
import json
try:
    import winreg
except ImportError:
    winreg = None

hosts = r"C:\Windows\System32\drivers\etc\hosts"
marker = "# MW_BLOCK"
block_entries = [
    "127.0.0.1 www.motivewave.com",
    "127.0.0.1 motivewave.com",
    "::1 www.motivewave.com",
    "::1 motivewave.com",
]

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(app_dir, "config.json")

def set_proxy(enable=True, host="127.0.0.1:8080"):
    if not winreg:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE)
        if enable:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, host)
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "localhost;127.0.0.1;<local>")
        else:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        
        # Notify WinInet of the change
        ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0) # INTERNET_OPTION_SETTINGS_CHANGED
        ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0) # INTERNET_OPTION_REFRESH
    except Exception as e:
        print(f"Error setting proxy: {e}")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("400x520")
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
        
        # Data Downloader Section
        dl_frame = tk.Frame(self, bg="#0a0a0a")
        dl_frame.pack(pady=(10, 0), fill="x", padx=20)
        
        tk.Label(dl_frame, text="HISTORICAL DATA DOWNLOADER", font=("Segoe UI", 8, "bold"), bg="#0a0a0a", fg="#555555").grid(row=0, column=0, columnspan=3, pady=(0, 5), sticky="w")
        
        tk.Label(dl_frame, text="Symbol:", font=("Segoe UI", 8), bg="#0a0a0a", fg="#aaaaaa").grid(row=1, column=0, sticky="w", pady=2)
        self.sym_var = tk.StringVar(value="ENQU6.CME")
        self.sym_entry = tk.Entry(dl_frame, textvariable=self.sym_var, font=("Segoe UI", 9), bg="#1a1a1a", fg="#ffffff", bd=1, relief="solid", insertbackground="white", width=15)
        self.sym_entry.grid(row=1, column=1, sticky="w", padx=5)

        tk.Label(dl_frame, text="Type:", font=("Segoe UI", 8), bg="#0a0a0a", fg="#aaaaaa").grid(row=2, column=0, sticky="w", pady=2)
        self.type_var = tk.StringVar(value="all")
        type_opts = ["all", "bar", "tick"]
        self.type_menu = tk.OptionMenu(dl_frame, self.type_var, *type_opts)
        self.type_menu.config(bg="#1a1a1a", fg="#ffffff", bd=1, relief="solid", highlightthickness=0, font=("Segoe UI", 8))
        self.type_menu["menu"].config(bg="#1a1a1a", fg="#ffffff")
        self.type_menu.grid(row=2, column=1, sticky="w", padx=5)

        self.dl_btn = tk.Button(dl_frame, text="DOWNLOAD", font=("Segoe UI", 8, "bold"), 
                        bg="#222222", fg="#ffffff", activebackground="#333333", activeforeground="#ffffff", 
                        bd=1, relief="solid", cursor="hand2", width=12, command=self.start_download)
        self.dl_btn.grid(row=1, column=2, rowspan=2, padx=10, sticky="nsew", pady=2)

        # Console output
        self.console = tk.Text(self, bg="#0e0e0e", fg="#999999", font=("Segoe UI", 7), bd=0, relief="flat", highlightthickness=0, height=8)
        self.console.pack(pady=(15, 10), padx=20, fill="x")
        self.console.insert(tk.END, "Ready.\n")
        self.console.config(state=tk.DISABLED)
        
        self.config_loaded = False
        self.profile_id = ""
        self.machine_id = ""
        self.build = "640"
        self.version = "7.0.26"
        self.mitm_proc = None
        # Download Progress
        self.prog_var = tk.DoubleVar(value=0.0)
        self.prog_bar = tk.Canvas(self, height=4, bg="#1a1a1a", highlightthickness=0)
        self.prog_bar.pack(fill="x", side="bottom")
        self.prog_rect = self.prog_bar.create_rectangle(0, 0, 0, 4, fill="#00ffcc", width=0)
        
        self.load_config()
        self.update_ui()
        
        if not self.config_loaded:
            threading.Thread(target=self.run_setup_proxy, daemon=True).start()

    def destroy(self):
        try:
            if hasattr(self, 'proxy_running'):
                self.proxy_running = False
            self.restore_startup_ini()
        except:
            pass
        super().destroy()

    def load_config(self):
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    self.profile_id = cfg.get("profile_id", "")
                    self.machine_id = cfg.get("machine_id", "")
                    self.build = cfg.get("build", "640")
                    self.version = cfg.get("version", "7.0.26")
                    if self.profile_id and self.machine_id:
                        self.config_loaded = True
                        return True
        except Exception as e:
            print(f"Error loading config: {e}")
        self.config_loaded = False
        return False

    def run_setup_proxy(self):
        self.log_msg("[SETUP] Config not found. Initializing setup mode...")
        
        # Modify startup.ini to force Java to use the proxy
        appdata = os.environ.get('APPDATA', '')
        mw_dir = os.path.join(appdata, 'MotiveWave')
        startup_ini = os.path.join(mw_dir, 'startup.ini')
        startup_bak = os.path.join(mw_dir, 'startup.ini.bak')
        
        if os.path.exists(startup_ini):
            try:
                import shutil
                shutil.copy2(startup_ini, startup_bak)
                with open(startup_ini, 'r') as f:
                    lines = f.readlines()
                with open(startup_ini, 'w') as f:
                    for line in lines:
                        if line.startswith('VM_ARGS='):
                            # Add proxy settings and tell Java to use Windows cert store
                            proxy_args = " -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=8080 -Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=8080 -Djavax.net.ssl.trustStoreType=Windows-ROOT"
                            f.write(line.strip() + proxy_args + "\n")
                        else:
                            f.write(line)
                self.log_msg("[SETUP] Injected proxy settings into MotiveWave startup.ini")
            except Exception as e:
                self.log_msg(f"[ERROR] Failed to modify startup.ini: {e}")
        else:
            self.log_msg("[WARNING] MotiveWave startup.ini not found. Proxy might not be picked up.")

        self.log_msg("[SETUP] Starting built-in proxy...")
        
        try:
            import socket
            import ssl
            import select
            import datetime
            import urllib.parse
            import re
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            
            # Generate a CA certificate
            self.log_msg("[SETUP] Generating SSL certificates...")
            ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "GhostWave CA")])
            ca_cert = (
                x509.CertificateBuilder()
                .subject_name(ca_name)
                .issuer_name(ca_name)
                .public_key(ca_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(ca_key, hashes.SHA256())
            )
            
            # Save CA cert and install into Windows trust store
            ca_cert_path = os.path.join(app_dir, "ghostwave_ca.cer")
            with open(ca_cert_path, "wb") as f:
                f.write(ca_cert.public_bytes(serialization.Encoding.DER))
            subprocess.run(["certutil", "-addstore", "root", ca_cert_path],
                          capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.log_msg("[SETUP] SSL certificate installed.")
            
            # Generate a cert for motivewave.com signed by our CA
            site_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            site_cert = (
                x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "www.motivewave.com")]))
                .issuer_name(ca_name)
                .public_key(site_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName("www.motivewave.com"),
                        x509.DNSName("motivewave.com"),
                        x509.DNSName("*.motivewave.com"),
                    ]),
                    critical=False,
                )
                .sign(ca_key, hashes.SHA256())
            )
            
            # Write cert and key to temp files for SSL context
            site_cert_pem = site_cert.public_bytes(serialization.Encoding.PEM)
            site_key_pem = site_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()
            )
            cert_file = os.path.join(app_dir, "_mw_cert.pem")
            key_file = os.path.join(app_dir, "_mw_key.pem")
            with open(cert_file, "wb") as f:
                f.write(site_cert_pem)
            with open(key_file, "wb") as f:
                f.write(site_key_pem)
            
            # Create SSL context for MITM
            mitm_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            mitm_ctx.load_cert_chain(cert_file, key_file)
            
            # Start proxy server
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", 8080))
            srv.listen(10)
            srv.settimeout(1.0)
            
            self.proxy_running = True
            self.proxy_captured = False
            self.log_msg("[SETUP] Proxy listening on 127.0.0.1:8080")
            self.log_msg("[SETUP] PLEASE START MOTIVEWAVE, THEN CLOSE IT.")
            self.after(0, lambda: self.btn.config(text="WAITING FOR CAPTURE...", state=tk.DISABLED))
            
            while self.proxy_running:
                try:
                    client_sock, addr = srv.accept()
                    threading.Thread(
                        target=self._handle_proxy_conn,
                        args=(client_sock, mitm_ctx),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except Exception:
                    break
            
            srv.close()
            
            # Cleanup temp files
            for f in [cert_file, key_file, ca_cert_path]:
                try:
                    os.remove(f)
                except:
                    pass
                    
        except Exception as e:
            self.log_msg(f"[ERROR] Proxy failed: {e}")
        
        self.restore_startup_ini()
        if self.load_config():
            self.after(0, self.update_ui)
    
    def _handle_proxy_conn(self, client_sock, mitm_ctx):
        """Handle a single proxy connection."""
        import socket
        import ssl
        import select
        import urllib.parse
        import re
        
        try:
            client_sock.settimeout(10)
            data = client_sock.recv(8192)
            if not data:
                client_sock.close()
                return
            
            first_line = data.split(b"\r\n")[0].decode("utf-8", errors="replace")
            
            if first_line.upper().startswith("CONNECT"):
                # HTTPS CONNECT tunnel
                parts = first_line.split()
                host_port = parts[1] if len(parts) > 1 else ""
                host = host_port.split(":")[0]
                port = int(host_port.split(":")[1]) if ":" in host_port else 443
                
                # Tell client the tunnel is established
                client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                
                self.log_msg(f"[DEBUG] CONNECT requested for: {host}:{port}")
                
                if "motivewave" in host.lower():
                    self._mitm_connection(client_sock, host, port, mitm_ctx)
                else:
                    self._tunnel_connection(client_sock, host, port)
            else:
                # Plain HTTP — just forward
                self._forward_http(client_sock, data)
        except Exception:
            pass
        finally:
            try:
                client_sock.close()
            except:
                pass
    
    def _mitm_connection(self, client_sock, host, port, mitm_ctx):
        """MITM an HTTPS connection to motivewave.com."""
        import socket
        import ssl
        import urllib.parse
        import re
        
        try:
            ssl_client = mitm_ctx.wrap_socket(client_sock, server_side=True)
        except Exception:
            return
        
        try:
            ssl_client.settimeout(10)
            
            # Read request headers
            req_data = b""
            while b"\r\n\r\n" not in req_data:
                chunk = ssl_client.recv(4096)
                if not chunk:
                    break
                req_data += chunk
                
            if not req_data:
                return
                
            # Extract Content-Length if present to read full body
            headers_part = req_data.split(b"\r\n\r\n", 1)[0].decode("utf-8", errors="replace")
            content_length = 0
            for line in headers_part.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":")[1].strip())
                    except:
                        pass
                        
            # Read remainder of body
            body_part = req_data.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in req_data else b""
            while len(body_part) < content_length:
                chunk = ssl_client.recv(4096)
                if not chunk:
                    break
                req_data += chunk
                body_part += chunk
            
            text = req_data.decode("utf-8", errors="replace")
            self.log_msg(f"[DEBUG] Intercepted request to motivewave.com ({len(text)} bytes)")
            
            # Check for license credentials anywhere in the request
            if "profile_id" in text and "machine_id" in text:
                body = text.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in text else text
                
                captured_profile = None
                captured_machine = None
                captured_build = "640"
                captured_version = "7.0.26"
                
                # Try URL-encoded form parsing
                try:
                    params = urllib.parse.parse_qs(body.strip())
                    if "profile_id" in params:
                        captured_profile = params["profile_id"][0]
                    if "machine_id" in params:
                        captured_machine = params["machine_id"][0]
                    if "build" in params:
                        captured_build = params["build"][0]
                    if "version" in params:
                        captured_version = params["version"][0]
                except:
                    pass
                
                # Fallback regex
                if not captured_profile:
                    m = re.search(r'profile_id=([^&\s]+)', body)
                    if m:
                        captured_profile = urllib.parse.unquote(m.group(1))
                if not captured_machine:
                    m = re.search(r'machine_id=([^&\s]+)', body)
                    if m:
                        captured_machine = urllib.parse.unquote(m.group(1))
                
                if captured_profile and captured_machine:
                    cfg = {
                        "profile_id": captured_profile,
                        "machine_id": captured_machine,
                        "build": captured_build,
                        "version": captured_version
                    }
                    with open(config_path, "w") as f:
                        json.dump(cfg, f, indent=4)
                    self.log_msg("[SETUP] Captured credentials!")
                    self.proxy_captured = True
                    self.proxy_running = False
            
            # Forward to real server regardless
            data = req_data
            try:
                real_ctx = ssl.create_default_context()
                real_ctx.check_hostname = False
                real_ctx.verify_mode = ssl.CERT_NONE
                real_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                real_sock.settimeout(10)
                real_ssl = real_ctx.wrap_socket(real_sock, server_hostname=host)
                real_ssl.connect((host, port))
                real_ssl.sendall(data)
                
                while True:
                    try:
                        resp = real_ssl.recv(8192)
                        if not resp:
                            break
                        ssl_client.sendall(resp)
                    except:
                        break
                real_ssl.close()
            except:
                # If we can't reach the real server, send a minimal response
                ssl_client.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                
        except Exception:
            pass
        finally:
            try:
                ssl_client.close()
            except:
                pass
    
    def _tunnel_connection(self, client_sock, host, port):
        """Transparent tunnel for non-motivewave connections."""
        import socket
        import select
        
        remote_sock = None
        try:
            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.settimeout(10)
            remote_sock.connect((host, port))
            
            socks = [client_sock, remote_sock]
            while self.proxy_running:
                readable, _, errs = select.select(socks, [], socks, 2)
                if errs:
                    break
                for s in readable:
                    data = s.recv(8192)
                    if not data:
                        return
                    if s is client_sock:
                        remote_sock.sendall(data)
                    else:
                        client_sock.sendall(data)
        except:
            pass
        finally:
            if remote_sock:
                try:
                    remote_sock.close()
                except:
                    pass
    
    def _forward_http(self, client_sock, initial_data):
        """Forward plain HTTP request."""
        import socket
        
        try:
            # Parse host from Host header
            headers = initial_data.decode("utf-8", errors="replace")
            host = "127.0.0.1"
            port = 80
            for line in headers.split("\r\n"):
                if line.lower().startswith("host:"):
                    hp = line.split(":", 1)[1].strip()
                    if ":" in hp:
                        host = hp.split(":")[0]
                        port = int(hp.split(":")[1])
                    else:
                        host = hp
                    break
            
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.settimeout(10)
            remote.connect((host, port))
            remote.sendall(initial_data)
            
            while True:
                resp = remote.recv(8192)
                if not resp:
                    break
                client_sock.sendall(resp)
            remote.close()
        except:
            pass

    def get_pos(self, e):
        self.xwin = self.winfo_x() - e.x_root
        self.ywin = self.winfo_y() - e.y_root

    def move_app(self, e):
        self.geometry(f"+{e.x_root + self.xwin}+{e.y_root + self.ywin}")

    def check(self):
        try:
            with open(hosts, 'r') as f:
                content = f.read()
                return marker in content
        except:
            return False

    def update_ui(self):
        self.prog_bar.coords(self.prog_rect, 0, 0, 0, 4)
        if not self.config_loaded:
            self.status_var.set("STATUS: SETUP REQUIRED")
            self.btn.config(text="INITIALIZING...", bg="#1a1a1a", state=tk.DISABLED)
            self.desc_var.set("Please START MotiveWave, then CLOSE it to capture details.\nGhostWave is intercepting the JVM traffic.")
            return

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
        
        # Instantly release license via MotiveWave API if we are dropping the connection
        if not blocked:
            try:
                import urllib.request
                import urllib.parse
                url = "https://www.motivewave.com/license/release.do"
                data = {
                    "build": self.build,
                    "profile_id": self.profile_id,
                    "machine_id": self.machine_id,
                    "version": self.version
                }
                encoded_data = urllib.parse.urlencode(data).encode('utf-8')
                req = urllib.request.Request(url, data=encoded_data)
                req.add_header('User-Agent', 'Java-http-client/26')
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')
                
                self.log_msg(f"\n[INFO] POST request sent to www.motivewave.com/license/release.do")
                self.log_msg(f"[INFO] Request Body: {data}")
                
                response = urllib.request.urlopen(req, timeout=5)
                status = response.getcode()
                resp_body = response.read().decode('utf-8').replace('\n', '').strip()
                
                self.log_msg(f"[SUCCESS] Server connection established (Status: {status})")
                self.log_msg(f"[SUCCESS] Server response: {resp_body}")
            except Exception as e:
                self.log_msg(f"[ERROR] API request failed: {str(e)}")

        try:
            with open(hosts, 'r') as f:
                data = f.readlines()
            
            # strip out any existing block lines
            cleaned = [d for d in data if marker not in d and not any(b in d for b in block_entries)]
            while cleaned and cleaned[-1].strip() == "":
                cleaned.pop()
            
            with open(hosts, 'w') as f:
                for d in cleaned:
                    f.write(d)
                if not blocked:
                    f.write("\n")
                    for entry in block_entries:
                        f.write(f"{entry} {marker}\n")
                else:
                    f.write("\n")
            
            subprocess.run(["ipconfig", "/flushdns"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
            
        self.is_loading = False

    def start_download(self):
        if self.is_loading: return
        self.is_loading = True
        self.dl_btn.config(state=tk.DISABLED, text="DOWNLOADING...")
        threading.Thread(target=self.do_download, daemon=True).start()

    def do_download(self):
        symbol = self.sym_var.get().strip()
        dtype = self.type_var.get()
        provider = "CQG"
        out_dir = os.path.join(os.getcwd(), "historical_data", provider, symbol)
        
        self.log_msg(f"\n[INFO] Fetching index for {symbol}...")
        
        try:
            import json
            import urllib.request
            
            BASE = "https://s3-us-west-2.amazonaws.com/elasticbeanstalk-us-west-2-200256718728/historical_data"
            HEADERS = {"User-Agent": "Java/26", "Accept": "*/*", "Connection": "keep-alive"}
            
            url = f"{BASE}/{provider}/{symbol}/index.json"
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=15)
            index = json.loads(resp.read().decode("utf-8"))
            
            files = [f for f in index if f != "index.json"]
            if dtype == "bar":
                files = [f for f in files if "bar_data" in f]
            elif dtype == "tick":
                files = [f for f in files if "tick_data" in f]
                
            os.makedirs(out_dir, exist_ok=True)
            self.log_msg(f"[INFO] Found {len(files)} files. Starting download...")
            
            total_kb = 0
            for i, filename in enumerate(files, 1):
                furl = f"{BASE}/{provider}/{symbol}/{filename}"
                freq = urllib.request.Request(furl, headers=HEADERS)
                fresp = urllib.request.urlopen(freq, timeout=30)
                path = os.path.join(out_dir, filename)
                with open(path, "wb") as f:
                    f.write(fresp.read())
                kb = os.path.getsize(path) / 1024
                total_kb += kb
                self.log_msg(f"  [{i}/{len(files)}] {filename} ({kb:.1f} KB)")
                
            self.log_msg(f"[SUCCESS] Saved {total_kb/1024:.1f} MB to {out_dir}")
        except Exception as e:
            self.log_msg(f"[ERROR] Download failed: {str(e)}")
            
        self.after(0, lambda: self.dl_btn.config(state=tk.NORMAL, text="DOWNLOAD"))
        self.is_loading = False

    def log_msg(self, msg):
        def _log():
            self.console.config(state=tk.NORMAL)
            self.console.insert(tk.END, msg + "\n")
            self.console.see(tk.END)
            self.console.config(state=tk.DISABLED)
        self.after(0, _log)

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
