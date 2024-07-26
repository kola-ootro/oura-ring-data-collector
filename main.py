import requests
import os
from datetime import datetime, timedelta
import json
from flask import Flask, render_template, redirect, url_for
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OURA_API_KEY = os.environ.get('OURA_API_KEY')
BASE_URL = "https://api.ouraring.com/v2/usercollection/"
DATA_FILE = "/tmp/oura_data.json"

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
        logger.info(f"Loaded data: {oura_data}")
        return render_template('template.html', oura_data=oura_data)
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
        return "Data updated successfully", 200
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
    logger.info("fetch_and_store_data completed successfully")

if __name__ == "__main__":
    if check_api_key():
        app.run(host='0.0.0.0', port=8080)
    else:
        print("Please set the OURA_API_KEY environment variable before running the application.")