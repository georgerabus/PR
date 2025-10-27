import threading, socket
def fetch():
    s = socket.create_connection(("127.0.0.1",8081))
    s.sendall(b"GET /drstone.jpg HTTP/1.1\r\nHost: host\r\nConnection: close\r\n\r\n")
    s.recv(4096)
    s.close()
threads=[]
for _ in range(20):
    th=threading.Thread(target=fetch); th.start(); threads.append(th)
for th in threads: th.join()