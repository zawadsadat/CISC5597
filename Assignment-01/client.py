# -*- coding:utf-8 -*-
import socket
import threading
import sys

ip_port = ('127.0.0.1', 9999)
s = socket.socket()
s.connect(ip_port)

# Receive and show assigned client ID
welcome = s.recv(1024).decode()
client_id = None
if welcome.startswith("CLIENT_ID:"):
    try:
        client_id = int(welcome.split(":", 1)[1])
        print(f"Connected. Assigned client ID = {client_id}")
    except ValueError:
        print("Connected. (Warning: could not parse client ID)")
else:
    print("Connected. (No client ID received)")

# Background receiver so forwarded messages arrive anytime
def _receiver():
    try:
        while True:
            data = s.recv(4096)
            if not data:
                print("\n[Disconnected]")
                break
            # Printing the incoming message
            print("\n" + data.decode())
    except Exception:
        pass


rt = threading.Thread(target=_receiver, daemon=True)
rt.start()

# Sender loop
try:
    while True:
        inp = input('input msg: ').strip()
        if not inp:
            continue
        s.sendall(inp.encode())
        if inp.lower() == "exit":
            break
except (KeyboardInterrupt, EOFError):
    try:
        s.sendall(b"exit")
    except Exception:
        pass
finally:
    s.close()
