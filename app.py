import os
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError
from client.nova_client import NovaDaxClient
import time
import threading
from datetime import datetime
import pytz

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 23
SCHEDULE_INTERVAL_HOURS = 2
COUNTDOWN_INTERVAL_SECONDS = 43200

MSG_API_RUNNING = "API is running!"
MSG_OUTSIDE_BUSINESS_HOURS = "Outside business hours. Order not executed."
MSG_SCHEDULED_ORDER_EXECUTED = "Order executed:"

app = Flask(__name__)

TZ = pytz.timezone("America/Sao_Paulo")

scheduler = BackgroundScheduler(timezone=TZ)

def get_current_hour():
    return datetime.now(TZ).hour

def scheduled_order():
    current_hour = get_current_hour()
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
        print(f'Time until next order: {int(hours)}:{int(minutes):02}:{int(seconds):02}', end='\r')
        time.sleep(1)

@app.route("/balance")
def balance():
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.get_total_assets_in_brl()
    return jsonify(data)

@app.route("/order")
def order():
    nova_client = NovaDaxClient(API_KEY, API_SECRET)
    data = nova_client.create_order()
    return jsonify(data)

@app.route("/")
def home():
    return jsonify({"message": MSG_API_RUNNING})

if __name__ == "__main__":
    try:
        scheduler.add_job(scheduled_order, "interval", hours=SCHEDULE_INTERVAL_HOURS)
        scheduler.start()
    except ConflictingIdError:
        print("Job already exists. Continuing execution...")
    
    timer_thread = threading.Thread(target=countdown_timer, args=(COUNTDOWN_INTERVAL_SECONDS,))
    timer_thread.daemon = True
    timer_thread.start()
    
    app.run(debug=True, host="0.0.0.0", port=5000)
