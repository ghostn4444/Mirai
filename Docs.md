## PROJECT 

```bahs
mirai-ptbr/
├── cnc/
│   ├── server.js          # TCP server principal
│   ├── protocol.js        # Parse do protocolo binário
│   ├── attack.js          # Gerenciamento de ataques
│   └── client.js          # CLI de comando
├── scanner/
│   ├── scanner.py         # SYN scan + brute force
│   ├── creds.py           # 62 credenciais padrão
│   └── state_machine.py   # Máquina de estados TCP
├── loader/
│   ├── loader.py          # wget/tftp deploy
│   └── serve.py           # Servidor HTTP estático
├── attacks/
│   ├── main.py            # Router de ataques
│   ├── udp.py
│   ├── syn.py
│   ├── dns.py
│   ├── http.py
│   └── vse.py
├── bot/
│   ├── bot.py             # Payload principal
│   └── build.sh           # Script de compilação
├── tools/
│   └── enc.py             # Ofuscador XOR
└── README.md
```