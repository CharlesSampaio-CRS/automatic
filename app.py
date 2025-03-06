from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError
from client.nova_client import NovaDaxClient
import time
import threading
from datetime import datetime
import pytz
import os 

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# Configurações de Agendamento
BUSINESS_HOURS_START = 9   # 9 AM
BUSINESS_HOURS_END = 23    # 11 PM
SCHEDULE_INTERVAL_HOURS = 2  # 2 horas
COUNTDOWN_INTERVAL_SECONDS = 43200  # 12 horas

# Mensagens
MSG_API_RUNNING = "API is running!"
MSG_OUTSIDE_BUSINESS_HOURS = "Outside of business hours. Scheduled order not executed."
MSG_SCHEDULED_ORDER_EXECUTED = "Scheduled order executed:"

app = Flask(__name__)

# Definir fuso horário
TZ = pytz.timezone("America/Sao_Paulo")

# Inicializar o agendador com fuso horário correto
scheduler = BackgroundScheduler(timezone=TZ)

def get_current_hour():
    """Obtém a hora atual no fuso horário configurado."""
    return datetime.now(TZ).hour

def scheduled_order():
    """Executa uma ordem programada dentro do horário comercial."""
    current_hour = get_current_hour()
    if BUSINESS_HOURS_START <= current_hour < BUSINESS_HOURS_END:
        nova_client = NovaDaxClient(API_KEY, API_SECRET)
        data = nova_client.create_order()
        print(f"{MSG_SCHEDULED_ORDER_EXECUTED} {data}")
    else:
        print(MSG_OUTSIDE_BUSINESS_HOURS)

def countdown_timer(interval):
    """Exibe um contador regressivo até a próxima execução programada."""
    while True:
        time_left = interval - (time.time() % interval)
        hours, remainder = divmod(time_left, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f'Time until next scheduled order: {int(hours)}:{int(minutes):02}:{int(seconds):02}', end='\r')
        time.sleep(1)

@app.route("/balance")
def balance():
    """Retorna o saldo total em BRL."""
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.get_total_assets_in_brl()
    return jsonify(data)

@app.route("/order")
def order():
    """Cria uma nova ordem."""
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.create_order()
    return jsonify(data)

@app.route("/")
def home():
    """Rota principal da API."""
    return jsonify({"message": MSG_API_RUNNING})

if __name__ == "__main__":
    # Iniciar o agendador
    try:
        scheduler.add_job(scheduled_order, "interval", hours=SCHEDULE_INTERVAL_HOURS)
        scheduler.start()
    except ConflictingIdError:
        print("Job já existe no scheduler. Continuando execução...")
    
    # Iniciar a thread do contador regressivo
    timer_thread = threading.Thread(target=countdown_timer, args=(COUNTDOWN_INTERVAL_SECONDS,))
    timer_thread.daemon = True
    timer_thread.start()
    
    # Rodar a aplicação Flask
    app.run(debug=True, host="0.0.0.0", port=5000)