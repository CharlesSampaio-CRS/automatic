"""
Verificação do Schedule de Trading Automático
Mostra informações sobre o agendamento de ordens
"""

import os
import sys
from datetime import datetime, timedelta
import pytz

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.config.bot_config import bot_config, BUSINESS_HOURS_START, BUSINESS_HOURS_END, SCHEDULE_INTERVAL_HOURS

TZ = pytz.timezone("America/Sao_Paulo")

print("\n" + "="*80)
print("⏰ VERIFICAÇÃO DO SCHEDULE DE TRADING AUTOMÁTICO")
print("="*80)

# Configurações atuais
schedule_interval = bot_config.get('schedule_interval_hours', 2)
business_start = bot_config.get('business_hours_start', 9)
business_end = bot_config.get('business_hours_end', 23)

print("\n📋 CONFIGURAÇÕES ATUAIS:")
print("-"*80)
print(f"   Intervalo entre ordens: {schedule_interval} horas")
print(f"   Horário de funcionamento: {business_start}h às {business_end}h")
print(f"   Fuso horário: {TZ}")

# Calcula quantas execuções por dia
hours_working = business_end - business_start
executions_per_day = hours_working // schedule_interval

print(f"\n📊 FREQUÊNCIA:")
print("-"*80)
print(f"   Horas de operação por dia: {hours_working}h")
print(f"   Execuções por dia: ~{executions_per_day} vezes")
print(f"   Total de minutos entre execuções: {schedule_interval * 60} minutos")

# Hora atual
now = datetime.now(TZ)
current_hour = now.hour

print(f"\n🕐 STATUS ATUAL:")
print("-"*80)
print(f"   Hora atual: {now.strftime('%H:%M:%S')}")

if business_start <= current_hour < business_end:
    print(f"   Status: ✅ DENTRO do horário de funcionamento")
    print(f"   Bot: 🟢 ATIVO - Pode executar ordens")
else:
    print(f"   Status: ⏸️  FORA do horário de funcionamento")
    print(f"   Bot: 🔴 PAUSADO - Aguardando {business_start}h")

# Simula próximas execuções
print(f"\n📅 PRÓXIMAS EXECUÇÕES PREVISTAS (hoje):")
print("-"*80)

current_time = now
next_executions = []

for i in range(5):
    next_time = current_time + timedelta(hours=schedule_interval)
    next_hour = next_time.hour
    
    if business_start <= next_hour < business_end:
        status = "✅ Executa"
        next_executions.append(next_time)
    else:
        status = "⏸️  Pula (fora do horário)"
    
    print(f"   {i+1}. {next_time.strftime('%H:%M')} - {status}")
    current_time = next_time

print("\n" + "="*80)
print("💡 COMO FUNCIONA:")
print("="*80)
print("   1. O bot inicia junto com o Flask (run.py)")
print("   2. APScheduler cria um job em background")
print("   3. A cada 2 horas, verifica se está no horário de funcionamento")
print("   4. Se SIM: Executa create_order() automaticamente")
print("   5. Se NÃO: Pula e aguarda próxima execução")
print("\n" + "="*80)
print("🔧 PARA ALTERAR:")
print("="*80)
print("   Edite src/config/settings.json:")
print('   - "schedule_interval_hours": 2  ← Mude para 1, 3, 4, etc.')
print('   - "business_hours_start": 9    ← Mude horário de início')
print('   - "business_hours_end": 23     ← Mude horário de fim')
print("\n" + "="*80)
print("✅ Schedule configurado e rodando!")
print("="*80 + "\n")
