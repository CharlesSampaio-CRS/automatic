from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from nova_client import NovaDaxClient
import time
import threading
from datetime import datetime

# Constantes de API
API_KEY = '5c5a2fa1-8419-4a99-aef7-87a3baef5fec'  # Local no commit
API_SECRET = 'WMqML2GNdchmtyGCkJ3aANrVQ35vIT9R'   # Local no commit

# Constantes de Agendamento
BUSINESS_HOURS_START = 9      # 9 AM
BUSINESS_HOURS_END = 23       # 11 PM
SCHEDULE_INTERVAL_HOURS = 2  #2 Hours
COUNTDOWN_INTERVAL_SECONDS = 43200  # 12 Hours

# Mensagens
MSG_API_RUNNING = "API is running!"
MSG_OUTSIDE_BUSINESS_HOURS = "Outside of business hours. Scheduled order not executed."
MSG_SCHEDULED_ORDER_EXECUTED = "Scheduled order executed:"

app = Flask(__name__)

def scheduled_order():
    current_hour = datetime.now().hour

    if BUSINESS_HOURS_START <= current_hour < BUSINESS_HOURS_END:
        nova_client = NovaDaxClient(API_KEY, API_SECRET)
        data = nova_client.create_order()
        print(f"{MSG_SCHEDULED_ORDER_EXECUTED} {data}")
    else:
        print(MSG_OUTSIDE_BUSINESS_HOURS)

def countdown_timer(interval):
    while True:
        time_left = interval - (time.time() % interval)
        hours, remainder = divmod(time_left, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f'Time until next scheduled order: {int(hours)}:{int(minutes):02}:{int(seconds):02}', end='\r')
        time.sleep(1)

@app.route("/balance")
def balance():
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.get_total_assets_in_brl()
    return data

@app.route("/order")
def order():
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.create_order()
    return data

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_order, trigger="interval", hours=SCHEDULE_INTERVAL_HOURS)
scheduler.start()

@app.route("/")
def home():
    return MSG_API_RUNNING

if __name__ == "__main__":
    timer_thread = threading.Thread(target=countdown_timer, args=(COUNTDOWN_INTERVAL_SECONDS,))
    timer_thread.daemon = True
    timer_thread.start()
    app.run(debug=True)
