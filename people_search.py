import os
import logging
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from flask import Flask, request, render_template
from googleapiclient.discovery import build
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG level for more detailed output

# The scopes your application needs
SCOPES = ['https://www.googleapis.com/auth/customsearch']

# Load credentials or authenticate
def authenticate_google_api():
    logging.debug("Authenticating Google API")
    creds = None
    if os.path.exists('/opt/token.json'):
        logging.debug("Token found at /opt/token.json, loading credentials")
        creds = Credentials.from_authorized_user_file('/opt/token.json', SCOPES)
    
    if not creds or not creds.valid:
        logging.debug("Credentials are invalid or missing")
        if creds and creds.expired and creds.refresh_token:
            logging.debug("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            logging.debug("No valid credentials, initiating OAuth flow")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    '/opt/credentials.json', SCOPES)
                logging.info(f"Using redirect URI: http://localhost:5000/callback")
                creds = flow.run_local_server(port=5000)
                with open('/opt/token.json', 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logging.error(f"Error during OAuth flow: {e}")
                raise
    
    logging.debug("Authentication successful")
    return creds

def google_search(query, creds):
    logging.debug(f"Performing Google search for query: {query}")
    cse_id = '90f74a59e07b84462'  
    service = build('customsearch', 'v1', credentials=creds)
    try:
        res = service.cse().list(q=query, cx=cse_id).execute()
        logging.debug(f"Search results: {res}")
        return res.get('items', [])
    except Exception as e:
        logging.error(f"Error during Google search: {e}")
        raise

def scrape_public_records(url):
    logging.debug(f"Scraping public records from URL: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Log the actual response or structure if needed
        logging.debug(f"Scraped HTML content: {soup.prettify()[:500]}")  # Log a portion of the HTML content

        # Update this part based on the actual structure of the target website
        for record in soup.find_all('div', class_='record-info'):
            name = record.find('h2').text.strip()
            address = record.find('span', class_='address').text.strip()
            logging.info(f'Name: {name}, Address: {address}')  # Log found records
    except requests.exceptions.RequestException as e:
        logging.error(f"Error while scraping: {e}")
        raise

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def index():
    logging.debug("Rendering index.html")
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        query = request.form['query']
        logging.info(f"Received search query: {query}")
        credentials = authenticate_google_api()
        results = google_search(query, credentials)
        logging.debug(f"Rendering results: {results}")
        return render_template('results.html', results=results)
    except Exception as e:
        logging.error(f"Error during search: {e}")
        logging.error(traceback.format_exc())  # Log the full stack trace
        return "An error occurred. Please try again later.", 500

if __name__ == "__main__":
    logging.info("Starting Flask app on port 5000")
    app.run(port=5000)

