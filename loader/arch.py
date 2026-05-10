import re
import socket
import time
import logging

log = logging.getLogger(__name__)

ARCH_MAP = {
    'armv4l':    'arm',
    'armv4tb':   'arm',
    'armv5l':    'arm',
    'armv5te':   'arm',
    'armv5tejl': 'arm',
    'armv6l':    'arm',
    'armv6j':    'arm',
    'armv7l':    'arm',
    'armv7m':    'arm',
    'armv8l':    'aarch64',
    'aarch64':   'aarch64',
    'i386':      'x86',
    'i486':      'x86',
    'i586':      'x86',
    'i686':      'x86',
    'x86_64':    'x86_64',
    'amd64':     'x86_64',
    'mips':      'mips',
    'mipsel':    'mips',
    'mips64':    'mips64',
    'ppc':       'ppc',
    'powerpc':   'ppc',
    'ppc64':     'ppc64',
    'sh4':       'sh4',
    'sparc':     'sparc',
    'm68k':      'm68k',
}

REVERSE_ARCH_MAP = {
    'arm':      ['armv4l', 'armv5l', 'armv6l', 'armv7l'],
    'aarch64':  ['aarch64'],
    'x86':      ['i686'],
    'x86_64':   ['x86_64'],
    'mips':     ['mips', 'mipsel'],
    'mips64':   ['mips64'],
    'ppc':      ['ppc', 'powerpc'],
    'ppc64':    ['ppc64'],
    'sh4':      ['sh4'],
    'sparc':    ['sparc'],
    'm68k':     ['m68k'],
}


def detect_arch_via_uname(host: str, port: int = 23, timeout: float = 5.0) -> tuple:
    """
    Conecta via telnet/raw socket, envia 'uname -m\\n' e captura output.
    Retorna (arquitetura_normalizada, raw_output) ou (None, None).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        time.sleep(1)

        # Limpa banner
        data = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                time.sleep(0.2)
        except socket.timeout:
            pass

        # Envia comando
        sock.send(b'uname -m\n')
        time.sleep(1)

        output = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                output += chunk
                time.sleep(0.3)
        except socket.timeout:
            pass

        sock.close()

        text = output.decode('utf-8', errors='replace')
        # Limpa sujeira do terminal
        text = re.sub(r'[^\w\.\-\+/]', '', text).strip().lower()

        for pattern, arch in sorted(ARCH_MAP.items(), key=lambda x: -len(x[0])):
            if pattern in text:
                log.info(f"Arquitetura detectada: {arch} (raw: {text})")
                return arch, text

        log.warning(f"Arquitetura não reconhecida: {text}")
        return None, text

    except Exception as e:
        log.debug(f"Erro detectando arch via uname em {host}:{port}: {e}")
        return None, None


def detect_arch_via_proc(host: str, port: int = 23, timeout: float = 5.0) -> tuple:
    """Tenta detectar arch via /proc/cpuinfo ou /proc/version."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        time.sleep(1)

        data = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                time.sleep(0.2)
        except socket.timeout:
            pass

        sock.send(b'cat /proc/cpuinfo\n')
        time.sleep(1)

        output = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                output += chunk
                time.sleep(0.3)
        except socket.timeout:
            pass

        sock.close()

        text = output.decode('utf-8', errors='replace').lower()

        # Procura por indicadores
        if 'aarch64' in text or 'armv8' in text:
            return 'aarch64', text[:200]
        if 'arm' in text:
            # Tenta identificar versão
            for v in ['v7', 'v6', 'v5', 'v4']:
                if v in text:
                    return f'arm{v}', text[:200]
            return 'arm', text[:200]
        if 'mips' in text:
            return 'mips', text[:200]
        if 'intel' in text or 'x86' in text or 'amd' in text:
            return 'x86_64' if '64' in text else 'x86', text[:200]

        return None, text[:200]

    except Exception as e:
        log.debug(f"Erro detectando arch via /proc em {host}:{port}: {e}")
        return None, None


def detect_arch(host: str, port: int = 23, timeout: float = 5.0) -> str:
    """Tenta múltiplos métodos de detecção de arquitetura."""
    arch, raw = detect_arch_via_uname(host, port, timeout)
    if arch:
        return arch

    arch, raw = detect_arch_via_proc(host, port, timeout)
    if arch:
        return arch

    # Fallback: tenta executar o binário e detecta pelo erro
    return 'arm'  # default seguro para IoT
