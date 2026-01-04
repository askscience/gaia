
import socket

def renew_tor_identity():
    """
    Sends a NEWNYM signal to the Tor control port.
    Returns:
        (True, "Success")
        (False, "ConnectionRefused") -> Port closed
        (False, "AuthFailed") -> Need password/cookie permissions
        (False, str) -> Error details
    """
    ports = [9051, 9151]
    last_error = None
    connection_refused = False
    
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect(('127.0.0.1', port))
                
                # Check required auth method
                s.sendall(b'PROTOCOLINFO 1\r\n')
                resp_data = b""
                while b"250 OK" not in resp_data:
                    chunk = s.recv(4096)
                    if not chunk: break
                    resp_data += chunk
                
                resp = resp_data.decode(errors='ignore')
                
                cookie_hex = ""
                
                # Look for COOKIEFILE="..."
                import re
                auth_match = re.search(r'AUTH METHODS=([^ ]+)', resp)
                path_match = re.search(r'COOKIEFILE="([^"]+)"', resp)
                
                methods = auth_match.group(1).split(",") if auth_match else []
                
                if "COOKIE" in methods and path_match:
                    cookie_path = path_match.group(1)
                    try:
                        with open(cookie_path, "rb") as f:
                            import binascii
                            cookie_bytes = f.read()
                            cookie_hex = binascii.hexlify(cookie_bytes).decode()
                    except PermissionError:
                        # Fallback to Password if Configured
                        from src.core.config import ConfigManager
                        config = ConfigManager()
                        pwd = config.get("tor_control_password", "")
                        if pwd:
                            s.sendall(f'AUTHENTICATE "{pwd}"\r\n'.encode())
                            resp = s.recv(1024).decode()
                            if resp.startswith("250"):
                                s.sendall(b'SIGNAL NEWNYM\r\n')
                                resp = s.recv(1024).decode()
                                if resp.startswith("250"): return True, "Success"
                                return False, "SignalFailed"
                            return False, f"AuthFailed (Password): {resp.strip()}"

                        return False, f"PermissionDenied: Cannot read {cookie_path}. Add user to tor group or enable hashed password."
                    except Exception as e:
                        print(f"[Tor] Error reading cookie: {e}")
                
                # Authenticate (Cookie or Password or Null)
                if cookie_hex:
                    s.sendall(f'AUTHENTICATE {cookie_hex}\r\n'.encode())
                else:
                    # Check for configured password first
                    from src.core.config import ConfigManager
                    config = ConfigManager()
                    pwd = config.get("tor_control_password", "")
                    
                    if pwd:
                         s.sendall(f'AUTHENTICATE "{pwd}"\r\n'.encode())
                    else:
                        # Try null/empty auth
                        s.sendall(b'AUTHENTICATE ""\r\n')
                    
                resp = s.recv(1024).decode()
                
                if not resp.startswith("250"):
                    print(f"[Tor] Auth failed on {port}: {resp}")
                    # If it was "Wrong length on authentication cookie", it means we sent "" but needed cookie
                    return False, f"AuthFailed: {resp.strip()}"
                    
                s.sendall(b'SIGNAL NEWNYM\r\n')
                resp = s.recv(1024).decode()
                
                if resp.startswith("250"):
                    return True, "Success"
                else:
                    return False, "SignalFailed"
                    
        except ConnectionRefusedError:
            connection_refused = True
            last_error = "ConnectionRefused"
            continue
        except Exception as e:
            last_error = str(e)
            continue
            
    if connection_refused:
         return False, "ConnectionRefused"
         
    return False, last_error or "UnknownError"
