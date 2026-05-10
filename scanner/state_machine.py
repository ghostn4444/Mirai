#!/usr/bin/env python3
"""
Máquina de estados TCP para scanner de conexão.
Implementa o mesmo padrão do Mirai original:
  - SYN_SENT: enviou SYN, aguardando SYN+ACK ou RST
  - SYN_ACK: recebeu SYN+ACK (porta aberta)
  - RST: recebeu RST (porta fechada)
  - TIMEOUT: sem resposta
  - CONNECTED: conexão estabelecida (login realizado)
"""

import enum
import time
import logging
from typing import Optional

log = logging.getLogger('scanner.state')


class TCPState(enum.IntEnum):
    """Estados da máquina TCP do scanner."""
    
    INIT = 0           # Estado inicial
    SYN_SENT = 1       # SYN enviado, aguardando resposta
    SYN_ACK = 2        # SYN+ACK recebido (porta aberta)
    RST = 3            # RST recebido (porta fechada)
    TIMEOUT = 4        # Timeout sem resposta
    CONNECTING = 5     # Conectando via TCP (após SYN_ACK)
    CONNECTED = 6      # Conexão estabelecida
    LOGIN_SENT = 7     # Credencial enviada
    LOGIN_OK = 8       # Login bem-sucedido
    LOGIN_FAIL = 9     # Login falhou
    BANNER = 10        # Recebendo banner
    COMPLETE = 99      # Scanner completo


class ScanTarget:
    """Representa um alvo sendo escaneado."""
    
    __slots__ = (
        'ip', 'port', 'state', 'state_time',
        'attempts', 'last_error', 'banner',
        'sock',
    )
    
    def __init__(self, ip: str, port: int = 23):
        self.ip = ip
        self.port = port
        self.state = TCPState.INIT
        self.state_time = time.time()
        self.attempts = 0
        self.last_error: Optional[str] = None
        self.banner: Optional[bytes] = None
        self.sock = None
    
    def transition(self, new_state: TCPState):
        """Transiciona para um novo estado."""
        old_state = self.state
        self.state = new_state
        self.state_time = time.time()
        log.debug(f"[*] {self.ip}:{self.port} {old_state.name} -> {new_state.name}")
    
    @property
    def elapsed_in_state(self) -> float:
        """Tempo no estado atual."""
        return time.time() - self.state_time
    
    @property
    def is_alive(self) -> bool:
        """Se o alvo ainda está sendo processado."""
        return self.state not in (TCPState.COMPLETE, TCPState.TIMEOUT, TCPState.RST)
    
    @property
    def is_open(self) -> bool:
        """Se a porta está aberta."""
        return self.state in (TCPState.SYN_ACK, TCPState.CONNECTING, 
                             TCPState.CONNECTED, TCPState.BANNER)
    
    @property
    def is_compromised(self) -> bool:
        """Se conseguimos acesso."""
        return self.state == TCPState.LOGIN_OK
    
    def __repr__(self):
        return f"ScanTarget({self.ip}:{self.port}, state={self.state.name})"


class StateMachine:
    """Gerencia múltiplos ScanTargets e suas transições."""
    
    def __init__(self):
        self.targets: dict[str, ScanTarget] = {}
    
    def add_target(self, ip: str, port: int = 23) -> ScanTarget:
        """Adiciona um novo alvo."""
        key = f"{ip}:{port}"
        if key not in self.targets:
            self.targets[key] = ScanTarget(ip, port)
        return self.targets[key]
    
    def get_target(self, ip: str, port: int = 23) -> Optional[ScanTarget]:
        """Obtém um alvo pelo IP."""
        return self.targets.get(f"{ip}:{port}")
    
    def update_state(self, ip: str, port: int, state: TCPState):
        """Atualiza o estado de um alvo."""
        target = self.get_target(ip, port)
        if target:
            target.transition(state)
    
    def get_active(self) -> list:
        """Retorna todos os alvos ativos (não completos/timeout)."""
        return [t for t in self.targets.values() if t.is_alive]
    
    def get_open(self) -> list:
        """Retorna alvos com porta aberta."""
        return [t for t in self.targets.values() if t.is_open]
    
    def get_compromised(self) -> list:
        """Retorna alvos comprometidos."""
        return [t for t in self.targets.values() if t.is_compromised]
    
    def stats(self) -> dict:
        """Estatísticas do scan."""
        return {
            'total': len(self.targets),
            'active': len(self.get_active()),
            'open': len(self.get_open()),
            'compromised': len(self.get_compromised()),
            'closed': sum(1 for t in self.targets.values() if t.state in (TCPState.RST,)),
            'timeout': sum(1 for t in self.targets.values() if t.state == TCPState.TIMEOUT),
        }
    
    def cleanup(self, max_age: float = 300):
        """Remove alvos antigos (mais de max_age segundos)."""
        now = time.time()
        to_remove = []
        for key, target in self.targets.items():
            if now - target.state_time > max_age:
                to_remove.append(key)
        for key in to_remove:
            del self.targets[key]


if __name__ == '__main__':
    # Teste rápido
    sm = StateMachine()
    sm.add_target('192.168.1.1')
    sm.add_target('192.168.1.2')
    sm.update_state('192.168.1.1', 23, TCPState.SYN_ACK)
    sm.update_state('192.168.1.2', 23, TCPState.RST)
    
    print(f"Stats: {sm.stats()}")
    print(f"Open: {sm.get_open()}")
