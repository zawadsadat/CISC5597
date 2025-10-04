# -*- coding:utf-8 -*-
import socket
import threading

ip_port = ('127.0.0.1', 9999)
sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sk.bind(ip_port)
sk.listen(5)

print('start socket server, waiting for clients...')

# Variables to store client ID
_client_id = 0
clients = {}
clients_lock = threading.Lock()

# Variables to store history
history = {}
history_lock = threading.Lock()

# To add the message into list
def _add_history(a, b, source_id, msg):
    key = (a, b) if a < b else (b, a)
    with history_lock:
        history.setdefault(key, []).append((source_id, msg))

# To retrive the message from list
def _get_history(a, b):
    key = (a, b) if a < b else (b, a)
    with history_lock:
        return list(history.get(key, []))

# Instructions setup
def link_handler(link, client_addr, my_id):
    try:
        while True:
            data = link.recv(4096)
            if not data:
                break
            msg = data.decode().strip()
            if not msg:
                continue


            # list
            if msg.lower() == "list":
                with clients_lock:
                    ids = sorted(clients.keys())
                link.sendall(("ACTIVE:" + ",".join(map(str, ids)) if ids else "ACTIVE:").encode())
                continue

            # exit
            if msg.lower() == "exit":
                try:
                    link.sendall(b"Goodbye")
                except Exception:
                    pass
                break

            # history <ID>
            if msg.lower().startswith("history "):
                parts = msg.split(None, 1)
                if len(parts) < 2 or not parts[1].isdigit():
                    link.sendall(b"ERROR: usage: history <ID>")
                    continue
                other_id = int(parts[1])
                conv = _get_history(my_id, other_id)
                if not conv:
                    link.sendall(f"No history with {other_id}".encode())
                else:
                    lines = [f"{src}: {content}" for (src, content) in conv]
                    link.sendall("\n".join(lines).encode())
                continue

            # Forward <ID> <message>
            if msg.startswith("Forward ") or msg.startswith("forward "):
                # Expected: Forward <ID> <message>
                parts = msg.split(None, 2)
                if len(parts) < 3 or not parts[1].isdigit():
                    link.sendall(b"ERROR: usage: Forward <ID> <message>")
                    continue
                target_id = int(parts[1])
                content = parts[2]

                with clients_lock:
                    target_sock = clients.get(target_id)

                if target_sock is None:
                    link.sendall(f"ERROR: target {target_id} not active".encode())
                    continue

                # record history for the pair
                _add_history(my_id, target_id, my_id, content)

                # deliver to target
                try:
                    target_sock.sendall(f"{my_id}: {content}".encode())
                except Exception:
                    link.sendall(f"ERROR: failed to deliver to {target_id}".encode())
                    continue


                link.sendall(f"DELIVERED to {target_id}".encode())
                continue


            link.sendall("server ack".encode())

    finally:
        with clients_lock:
            clients.pop(my_id, None)
        link.close()


while True:
    conn, address = sk.accept()
    # assign and send unique ID
    _client_id += 1
    my_id = _client_id
    try:
        conn.sendall(f"CLIENT_ID:{my_id}".encode())
    except Exception:
        conn.close()
        continue

    with clients_lock:
        clients[my_id] = conn

    t = threading.Thread(target=link_handler, args=(conn, address, my_id), daemon=True)
    t.start()
