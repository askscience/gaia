
import socket

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', port))
        is_open = result == 0
        print(f"Port {port}: {'OPEN' if is_open else 'CLOSED'}")
        return is_open

print("Checking common Tor ports...")
check_port(9050) # System Tor SOCKS
check_port(9150) # Tor Browser SOCKS
check_port(9051) # System Tor Control
check_port(9151) # Tor Browser Control
