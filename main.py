import requests
import os
from datetime import datetime, timedelta
import json
from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler

OURA_API_KEY = os.environ['OURA_API_KEY']
BASE_URL = "https://api.ouraring.com/v2/usercollection/"
DATA_FILE = "oura_data.json"

app = Flask(__name__, template_folder='templates')

def fetch_oura_data(data_type, start_date, end_date):
    url = f"{BASE_URL}{data_type}"
    headers = {
        "Authorization": f"Bearer {OURA_API_KEY}"
    }
    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {data_type} data: {response.status_code}")
        return None

def store_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
        print(f"Data successfully stored in {DATA_FILE}")
    except Exception as e:
        print(f"Error storing data: {e}")

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def update_data(new_data):
    existing_data = load_data()
    for data_type, data in new_data.items():
        if data_type not in existing_data:
            existing_data[data_type] = data
        else:
            existing_data[data_type]['data'].extend(data['data'])
    store_data(existing_data)

def fetch_and_store_data():
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)  # Fetch last 7 days of data

    data_types = ["daily_activity", "daily_readiness", "daily_sleep"]
    new_data = {}

    for data_type in data_types:
        data = fetch_oura_data(data_type, start_date, end_date)
        if data:
            new_data[data_type] = data

    update_data(new_data)
    print("Data updated successfully")

@app.route('/')
def display_data():
    oura_data = load_data()
    return render_template('template.html', oura_data=oura_data)

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_data, 'cron', hour='0,12')  # Run at 00:00 and 12:00
    scheduler.start()

    fetch_and_store_data()  # Fetch data immediately on startup
    app.run(host='0.0.0.0', port=8080)