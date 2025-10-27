import socket
import os
import sys
import mimetypes
from pathlib import Path
from urllib.parse import unquote

def generate_directory_listing(directory_path, url_path):
    """Generate HTML directory listing"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory listing for {url_path}</title>
     <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
<h1>📚 Welcome to My PDF Library</h1>
<p>This is my file server!</p>
<hr>
<ul>
"""
    
    # Add parent directory link if not root
    if url_path != '/':
        parent = '/'.join(url_path.rstrip('/').split('/')[:-1]) or '/'
        html += f'<li><a href="{parent}">Parent Directory</a></li>\n'
    
    # List directory contents
    try:
        items = sorted(os.listdir(directory_path))
        for item in items:
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                html += f'<li>📁 <a href="{url_path.rstrip("/")}/{item}/">{item}/</a></li>\n'
            else:
                html += f'<li>📄 <a href="{url_path.rstrip("/")}/{item}">{item}</a></li>\n'
    except Exception as e:
        html += f'<li>Error reading directory: {e}</li>\n'
    
    html += """</ul>
<hr>
</body>
</html>"""
    return html

def get_content_type(file_path):
    """Determine content type based on file extension"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type
    
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.css': 'text/css',
        '.js': 'application/javascript',
        # '.txt': 'text/html'
    }
    return content_types.get(ext, 'application/octet-stream')

def handle_request(client_socket, base_directory):
    """Handle a single HTTP request"""
    try:
        # Receive the request
        request = client_socket.recv(4096).decode('utf-8')
        
        if not request:
            return
        
        # Parse the request line
        lines = request.split('\r\n')
        request_line = lines[0]
        print(f"Request: {request_line}")
        
        # Extract method and path
        parts = request_line.split()
        if len(parts) < 2:
            send_response(client_socket, 400, b"Bad Request")
            return
        
        method = parts[0]
        url_path = unquote(parts[1])
        
        # Only handle GET requests
        if method != 'GET':
            send_response(client_socket, 405, b"Method Not Allowed")
            return
        
        # Remove leading slash and resolve path
        relative_path = url_path.lstrip('/') if url_path != '/' else ''
        file_path = os.path.normpath(os.path.join(base_directory, relative_path))
        
        # Security check: ensure path is within base directory
        if not file_path.startswith(os.path.abspath(base_directory)):
            send_response(client_socket, 403, b"Forbidden")
            return
        
        # Check if path exists
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                html_content = generate_directory_listing(file_path, url_path)
                send_response(client_socket, 200, html_content.encode('utf-8'), 'text/html')
            else:
                # Read and send file
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    content_type = get_content_type(file_path)
                    send_response(client_socket, 200, content, content_type)
                except Exception as e:
                    print(f"Error reading file: {e}")
                    send_response(client_socket, 500, b"Internal Server Error")
        else:
            send_response(client_socket, 404, b"404 Not Found")

    
    except Exception as e:
        print(f"Error handling request: {e}")
        try:
            send_response(client_socket, 500, b"Internal Server Error")
        except:
            pass

def send_response(client_socket, status_code, body, content_type=None):
    """Send HTTP response"""
    status_messages = {
        200: 'OK',
        400: 'Bad Request',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        500: 'Internal Server Error'
    }
    
    status_message = status_messages.get(status_code, 'Unknown')
    
    # If content type not specified, try to detect
    if content_type is None:
        content_type = 'text/html' if status_code != 200 else 'application/octet-stream'
    
    response = f"HTTP/1.1 {status_code} {status_message}\r\n"
    response += f"Content-Type: {content_type}\r\n"
    response += f"Content-Length: {len(body)}\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    
    client_socket.send(response.encode('utf-8'))
    client_socket.send(body)

def main():
    if len(sys.argv) != 2:
        print("Usage: python server.py <directory>")
        sys.exit(1)
    
    base_directory = sys.argv[1]
    
    if not os.path.isdir(base_directory):
        print(f"Error: {base_directory} is not a valid directory")
        sys.exit(1)
    
    base_directory = os.path.abspath(base_directory)
    
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to port
    port = 8000
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    
    print(f"Server listening on port {port}")
    print(f"Serving directory: {base_directory}")
    
    try:
        while True:
            # Accept connection
            client_socket, address = server_socket.accept()
            print(f"\nConnection from {address}")
            
            # Handle request
            handle_request(client_socket, base_directory)
            
            # Close connection
            client_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

if __name__ == '__main__':
    main()