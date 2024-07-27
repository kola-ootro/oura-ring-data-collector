import requests
import os
from datetime import datetime, timedelta
import json
from flask import Flask, render_template, redirect, url_for, send_file
import sys
import logging
import traceback
import pandas as pd
import io

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OURA_API_KEY = os.environ.get('OURA_API_KEY')
BASE_URL = "https://api.ouraring.com/v2/usercollection/"
DATA_FILE = "/tmp/oura_data.json"
LAST_UPDATED_FILE = "/tmp/last_updated.txt"

app = Flask(__name__, template_folder='templates')

def check_api_key():
    """Check if the Oura API key is set in environment variables."""
    if OURA_API_KEY:
        logger.info("OURA_API_KEY is set in environment variables.")
        return True
    else:
        logger.error("OURA_API_KEY is not set in environment variables.")
        return False

@app.route('/')
def display_data():
    """Route to display the Oura Ring data."""
    logger.info("Accessing root route")
    if not check_api_key():
        return "Error: OURA_API_KEY is not set", 500
    try:
        oura_data = load_data()
        if not oura_data:
            logger.info("No data found. Redirecting to fetch initial data.")
            return redirect(url_for('fetch_initial_data'))
        last_updated = load_last_updated_time()
        logger.info(f"Loaded data: {oura_data}")
        return render_template('template.html', oura_data=oura_data, last_updated=last_updated)
    except Exception as e:
        logger.error(f"Error in display_data: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred: {str(e)}", 500

@app.route('/update', methods=['GET'])
def manual_update():
    """Route to manually trigger data update."""
    logger.info("Accessing update route")
    if not check_api_key():
        return "Error: OURA_API_KEY is not set", 500
    try:
        fetch_and_store_data()
        return redirect(url_for('display_data'))
    except Exception as e:
        logger.error(f"Error in manual_update: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred during update: {str(e)}", 500

@app.route('/fetch_initial_data')
def fetch_initial_data():
    """Route to fetch initial data if none exists."""
    logger.info("Fetching initial data")
    if not check_api_key():
        return "Error: OURA_API_KEY is not set", 500
    try:
        fetch_and_store_data()
        return redirect(url_for('display_data'))
    except Exception as e:
        logger.error(f"Error fetching initial data: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred while fetching initial data: {str(e)}", 500

@app.route('/download_archive')
def download_archive():
    """Route to download all data as an Excel file."""
    logger.info("Accessing download archive route")
    if not check_api_key():
        return "Error: OURA_API_KEY is not set", 500
    try:
        oura_data = load_data()
        if not oura_data:
            logger.info("No data found for download.")
            return "No data available for download", 404

        # Create a Pandas Excel writer using XlsxWriter as the engine
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for data_type, data in oura_data.items():
                df = pd.DataFrame(data['data'])
                df.to_excel(writer, sheet_name=data_type, index=False)

        output.seek(0)
        return send_file(output, 
                         download_name='oura_data_archive.xlsx', 
                         as_attachment=True, 
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.error(f"Error in download_archive: {str(e)}")
        logger.error(traceback.format_exc())
        return f"An error occurred during archive download: {str(e)}", 500

def fetch_oura_data(data_type, start_date, end_date):
    """Fetch data from Oura API for a specific type and date range."""
    logger.info(f"Fetching {data_type} data from {start_date} to {end_date}")
    if not OURA_API_KEY:
        logger.error("OURA_API_KEY is not set in environment variables")
        raise ValueError("OURA_API_KEY is not set in environment variables")

    url = f"{BASE_URL}{data_type}"
    headers = {"Authorization": f"Bearer {OURA_API_KEY}"}
    params = {"start_date": start_date, "end_date": end_date}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching data from Oura API: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def store_data(data):
    """Store the fetched data to a file."""
    logger.info(f"Storing data to {DATA_FILE}")
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except IOError as e:
        logger.error(f"Error writing to data file: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def load_data():
    """Load data from the storage file."""
    logger.info(f"Loading data from {DATA_FILE}")
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Data file not found: {DATA_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from data file: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def update_data(new_data):
    """Update the stored data with new data."""
    logger.info("Updating data")
    existing_data = load_data()
    for data_type, data in new_data.items():
        if data_type not in existing_data:
            existing_data[data_type] = data
        else:
            existing_data[data_type]['data'].extend(data['data'])
    store_data(existing_data)

def fetch_and_store_data():
    """Fetch new data from Oura API and store it."""
    logger.info("Starting fetch_and_store_data")
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    data_types = ["daily_activity", "daily_readiness", "daily_sleep"]
    new_data = {}

    for data_type in data_types:
        try:
            data = fetch_oura_data(data_type, str(start_date), str(end_date))
            if data:
                new_data[data_type] = data
        except Exception as e:
            logger.error(f"Error fetching {data_type} data: {str(e)}")
            logger.error(traceback.format_exc())

    update_data(new_data)
    store_last_updated_time()
    logger.info("fetch_and_store_data completed successfully")

def store_last_updated_time():
    """Store the last updated time."""
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LAST_UPDATED_FILE, 'w') as f:
        f.write(last_updated)

def load_last_updated_time():
    """Load the last updated time."""
    try:
        with open(LAST_UPDATED_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Never"

if __name__ == "__main__":
    if check_api_key():
        app.run(host='0.0.0.0', port=8080)
    else:
        print("Please set the OURA_API_KEY environment variable before running the application.")