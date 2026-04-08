import socket
import select
import sys
import threading

def forward(source, destination):
    while True:
        try:
            data = source.recv(4096)
            if len(data) == 0:
                break
            destination.sendall(data)
        except Exception:
            break
    try:
        source.close()
    except Exception:
        pass
    try:
        destination.close()
    except Exception:
        pass

def main():
    if len(sys.argv) != 4:
        print("Usage: port_forward.py <listen_port> <target_host> <target_port>")
        sys.exit(1)

    listen_port = int(sys.argv[1])
    target_host = sys.argv[2]
    target_port = int(sys.argv[3])

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable address reuse
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server.bind(('0.0.0.0', listen_port))
    server.listen(100)
    print(f"Proxy listening on 0.0.0.0:{listen_port} forwarding to {target_host}:{target_port}")

    while True:
        try:
            client_socket, addr = server.accept()
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((target_host, target_port))

            t1 = threading.Thread(target=forward, args=(client_socket, target_socket))
            t2 = threading.Thread(target=forward, args=(target_socket, client_socket))

            t1.daemon = True
            t2.daemon = True

            t1.start()
            t2.start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error accepts: {e}")

if __name__ == '__main__':
    main()
