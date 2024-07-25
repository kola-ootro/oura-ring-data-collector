    import requests
    import os
    from datetime import datetime, timedelta
    import json
    from flask import Flask, render_template
    import sys

    OURA_API_KEY = os.environ.get('OURA_API_KEY')
    BASE_URL = "https://api.ouraring.com/v2/usercollection/"
    DATA_FILE = "/tmp/oura_data.json"

    app = Flask(__name__, template_folder='templates')

    @app.route('/')
    def display_data():
        try:
            oura_data = load_data()
            return render_template('template.html', oura_data=oura_data)
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    @app.route('/update', methods=['GET'])
    def manual_update():
        try:
            fetch_and_store_data()
            return "Data updated successfully", 200
        except Exception as e:
            return f"An error occurred during update: {str(e)}", 500

    def fetch_oura_data(data_type, start_date, end_date):
        if not OURA_API_KEY:
            raise ValueError("OURA_API_KEY is not set in environment variables")

        url = f"{BASE_URL}{data_type}"
        headers = {"Authorization": f"Bearer {OURA_API_KEY}"}
        params = {"start_date": start_date, "end_date": end_date}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # This will raise an HTTPError for bad responses
        return response.json()

    def store_data(data):
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)

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
        start_date = end_date - timedelta(days=7)

        data_types = ["daily_activity", "daily_readiness", "daily_sleep"]
        new_data = {}

        for data_type in data_types:
            data = fetch_oura_data(data_type, str(start_date), str(end_date))
            if data:
                new_data[data_type] = data

        update_data(new_data)

    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=8080)