#!/usr/bin/env python3
import socket
import sys
import os

DEFAULT_SAVE_DIR = "./downloads"

def parse_response(response_data):
    parts = response_data.split(b"\r\n\r\n", 1)
    if len(parts) != 2:
        return None, None, None

    headers_text = parts[0].decode("utf-8", errors="ignore")
    body = parts[1]

    lines = headers_text.split("\r\n")
    status_line = lines[0].split(" ")
    try:
        status_code = int(status_line[1])
    except:
        return None, None, None

    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.lower().strip()] = v.strip()

    return status_code, headers, body


def send_request(host, port, path):
    if not path.startswith("/"):
        path = "/" + path

    if "." not in os.path.basename(path) and not path.endswith("/"):
        path += "/"

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(request.encode("utf-8"))

    response = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    s.close()
    return response


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def main():
    if len(sys.argv) < 4:
        print("Usage: python client.py <server_host> <server_port> <url_path> [save_directory]")
        print("Example: python client.py localhost 8000 /extra")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    url_path = sys.argv[3]
    save_dir = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_SAVE_DIR

    ensure_dir(save_dir)

    print(f"Requesting http://{host}:{port}{url_path}")

    response = send_request(host, port, url_path)
    status, headers, body = parse_response(response)

    if status is None:
        print("✘ Invalid HTTP response")
        sys.exit(1)

    print(f"Status: {status}")

    if status != 200:
        print(body.decode(errors="ignore"))
        sys.exit(1)

    content_type = headers.get("content-type", "")

    if "text/html" in content_type:
        html = body.decode("utf-8", errors="ignore")

        items = []
        for line in html.splitlines():
            line = line.strip()
            if "<a " in line and "href=" in line:
                start = line.find("href=") + 6  
                end = line.find('"', start)
                href = line[start:end]
                if href:
                    items.append(href)

        print("Directory contents:")
        for item in items:
            print(item)
        return


    filename = os.path.basename(url_path.rstrip("/")) or "download"
    if "pdf" in content_type and not filename.endswith(".pdf"):
        filename += ".pdf"
    elif "png" in content_type and not filename.endswith(".png"):
        filename += ".png"

    path = os.path.join(save_dir, filename)
    with open(path, "wb") as f:
        f.write(body)

    print(f"✔ Saved: {path}")
    print(f"Bytes: {len(body)}")


if __name__ == "__main__":
    main()
