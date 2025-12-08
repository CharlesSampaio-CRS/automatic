#!/bin/bash

# Hourly Balance Snapshot Scheduler
# Executa o script de snapshot a cada hora fechada
# Para macOS/Linux usando cron

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON="$VENV_PATH/bin/python"
SNAPSHOT_SCRIPT="$SCRIPT_DIR/hourly_balance_snapshot.py"
LOG_FILE="$PROJECT_ROOT/logs/hourly_snapshot.log"

# Criar diretório de logs se não existir
mkdir -p "$PROJECT_ROOT/logs"

# Executar snapshot
echo "========================================" >> "$LOG_FILE"
echo "Starting hourly snapshot: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

cd "$PROJECT_ROOT"
"$PYTHON" "$SNAPSHOT_SCRIPT" >> "$LOG_FILE" 2>&1

echo "Finished: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
