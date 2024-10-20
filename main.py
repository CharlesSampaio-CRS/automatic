from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from nova_client import NovaDaxClient
import time
import threading
from datetime import datetime
import csv

# Constantes
API_KEY = 'XXX'
API_SECRET = 'xxx'
BUSINESS_HOURS_START = 9  # 9 AM
BUSINESS_HOURS_END = 23   # 11 PM
SCHEDULE_INTERVAL_HOURS = 2
COUNTDOWN_INTERVAL_SECONDS = 43200  # 12 hours

app = Flask(__name__)

def save_log_to_csv(message, status):
    with open('execution_log.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%d/%m/%Y %H:%M:%S"), message, status])

def scheduled_order():
    current_hour = datetime.now().hour

    if BUSINESS_HOURS_START <= current_hour < BUSINESS_HOURS_END:
        nova_client = NovaDaxClient(API_KEY, API_SECRET)
        data = nova_client.create_order()
        log_message = f"Scheduled order executed: {data}"
        save_log_to_csv(log_message, "Executed")
        print(log_message)
    else:
        log_message = "Outside of business hours. Scheduled order not executed."
        save_log_to_csv(log_message, "Not Executed")
        print(log_message)

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
    data = nova_client.get_non_zero_sorted_assets()
    return {'assets': data}

@app.route("/order")
def order():
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.create_order()
    return data

# Configuração do scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_order, trigger="interval", hours=SCHEDULE_INTERVAL_HOURS)
scheduler.start()

@app.route("/")
def home():
    return "API is running!"

if __name__ == "__main__":
    timer_thread = threading.Thread(target=countdown_timer, args=(COUNTDOWN_INTERVAL_SECONDS,))
    timer_thread.daemon = True
    timer_thread.start()
    app.run(debug=True)
