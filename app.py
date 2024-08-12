from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import pandas as pd
from urllib.parse import urlparse
from tld import get_tld
import re
import joblib
import os
import sqlite3
import csv
import io
import time
import shutil
import tempfile
import requests
import pandas as pd
import pickle
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from flask import flash 
from scipy.sparse import hstack, csr_matrix
from joblib import Parallel, delayed


app = Flask(__name__)

# Load the trained model (Random Forest model)
rfc_model = joblib.load('rfc_model.pkl')
filename = 'naive_bayes_url_classifier.sav'
loaded_model = pickle.load(open(filename, 'rb'))
model = joblib.load('url_classifier_model.pkl')
vectorizer = joblib.load('tfidf_vectorizer.pkl')


# Define functions for data preprocessing and prediction
def extractfeatures(url):
    features = {}
    try:
        parsed_url = urlparse(url)
        features['url_length'] = len(str(url))
        features['hostname_length'] = len(parsed_url.netloc)
        features['path_length'] = len(parsed_url.path)
        
        urlpath = parsed_url.path
        features['fd_length'] = len(urlpath.split('/')[1]) if len(urlpath.split('/')) > 1 else 0
        
        tld = get_tld(url, fail_silently=True)
        features['tld_length'] = len(tld) if tld else -1
        
        features['count-'] = url.count('-')
        features['count@'] = url.count('@')
        features['count?'] = url.count('?')
        features['count%'] = url.count('%')
        features['count.'] = url.count('.')
        features['count='] = url.count('=')
        features['count-http'] = url.count('http')
        features['count-https'] = url.count('https')
        features['count-www'] = url.count('www')
        
        features['count-digits'] = sum(c.isnumeric() for c in url)
        features['count-letters'] = sum(c.isalpha() for c in url)
        features['count_dir'] = parsed_url.path.count('/')
        
        features['use_of_ip'] = 1 if re.search(r'(([01]?\d\d?|2[0-4]\d|25[0-5])\.){3}([01]?\d\d?|2[0-4]\d|25[0-5])', url) else 0
        features['short_url'] = 1 if re.search(r'bit\.ly|goo\.gl|shorte\.st|go2l\.ink|x\.co|ow\.ly|t\.co|tinyurl|tr\.im|is\.gd|cli\.gs|yfrog\.com|migre\.me|ff\.im|tiny\.cc|url4\.eu|twit\.ac|su\.pr|twurl\.nl|snipurl\.com|short\.to|BudURL\.com|ping\.fm|post\.ly|Just\.as|bkite\.com|snipr\.com|fic\.kr|loopt\.us|doiop\.com|short\.ie|kl\.am|wp\.me|rubyurl\.com|om\.ly|to\.ly|bit\.do|t\.co|lnkd\.in|db\.tt|qr\.ae|adf\.ly|goo\.gl|bitly\.com|cur\.lv|tinyurl\.com|ow\.ly|bit\.ly|ity\.im|q\.gs|is\.gd|po\.st|bc\.vc|twitthis\.com|u\.to|j\.mp|buzurl\.com|cutt\.us|u\.bb|yourls\.org|x\.co|prettylinkpro\.com|scrnch\.me|filoops\.info|vzturl\.com|qr\.net|1url\.com|tweez\.me|v\.gd|tr\.im|link\.zip\.net', url) else 0
    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        features = {k: 0 for k in ['url_length', 'hostname_length', 'path_length', 'fd_length', 'tld_length',
                                   'count-', 'count@', 'count?', 'count%', 'count.', 'count=', 'count-http', 
                                   'count-https', 'count-www', 'count-digits', 'count-letters', 'count_dir',
                                   'use_of_ip', 'short_url']}
    return features

def fd_length(url):
    urlpath= urlparse(url).path
    try:
        return len(urlpath.split('/')[1])
    except:
        return 0

def tld_length(tld):
    try:
        return len(tld)
    except:
        return -1

def digit_count(url):
    digits = 0
    for i in url:
        if i.isnumeric():
            digits = digits + 1
    return digits

def letter_count(url):
    letters = 0
    for i in url:
        if i.isalpha():
            letters = letters + 1
    return letters

def no_of_dir(url):
    urldir = urlparse(url).path
    return urldir.count('/')

def having_ip_address(url):
    match = re.search('(([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\.([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\.([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\.'
        '([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\/)|'  
        '((0x[0-9a-fA-F]{1,2})\\.(0x[0-9a-fA-F]{1,2})\\.(0x[0-9a-fA-F]{1,2})\\.(0x[0-9a-fA-F]{1,2})\\/)' 
        '(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}', url)
    if match:
        return -1
    else:
        return 1

def shortening_service(url):
    match = re.search('bit\.ly|goo\.gl|shorte\.st|go2l\.ink|x\.co|ow\.ly|t\.co|tinyurl|tr\.im|is\.gd|cli\.gs|'
                      'yfrog\.com|migre\.me|ff\.im|tiny\.cc|url4\.eu|twit\.ac|su\.pr|twurl\.nl|snipurl\.com|'
                      'short\.to|BudURL\.com|ping\.fm|post\.ly|Just\.as|bkite\.com|snipr\.com|fic\.kr|loopt\.us|'
                      'doiop\.com|short\.ie|kl\.am|wp\.me|rubyurl\.com|om\.ly|to\.ly|bit\.do|t\.co|lnkd\.in|'
                      'db\.tt|qr\.ae|adf\.ly|goo\.gl|bitly\.com|cur\.lv|tinyurl\.com|ow\.ly|bit\.ly|ity\.im|'
                      'q\.gs|is\.gd|po\.st|bc\.vc|twitthis\.com|u\.to|j\.mp|buzurl\.com|cutt\.us|u\.bb|yourls\.org|'
                      'x\.co|prettylinkpro\.com|scrnch\.me|filoops\.info|vzturl\.com|qr\.net|1url\.com|tweez\.me|v\.gd|'
                      'tr\.im|link\.zip\.net', url)
    if match:
        return -1
    else:
        return 1

def copy_database_to_temp(path):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, os.path.basename(path))
    shutil.copy2(path, temp_path)
    return temp_path

def get_history(browser):
    history = []
    path = None

    if browser == 'chrome':
        path = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data\Default\History'
    elif browser == 'edge':
        path = os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data\Default\History'
    elif browser == 'tor':
        path = r'C:\Users\prath\Desktop\Tor Browser\Browser\TorBrowser\Data\Browser\profile.default\places.sqlite'
    elif browser == 'opera':
        path = os.path.expanduser('~') + r'\AppData\Roaming\Opera Software\Opera GX Stable\History'
    elif browser == 'brave':
        path = os.path.expanduser('~') + r'\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History'
    elif browser == 'firefox':
        path = os.path.expanduser('~') + r'\AppData\Roaming\Mozilla\Firefox\Profiles\<your-profile-folder>\places.sqlite'  # Update with the actual profile folder


    if path and os.path.exists(path):
        retries = 5
        while retries > 0:
            try:
                # Copy the database file to a temporary location
                temp_path = copy_database_to_temp(path)

                conn = sqlite3.connect(f'file:{temp_path}?mode=ro', uri=True)
                cursor = conn.cursor()
                if browser == 'tor' or browser == 'firefox':
                    cursor.execute("SELECT url, title, visit_count, datetime(last_visit_date/1000000, 'unixepoch', 'localtime') as last_visit FROM moz_places")
                else:
                    cursor.execute("SELECT url, title, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as last_visit FROM urls")
                history = cursor.fetchall()
                conn.close()
                os.remove(temp_path)  # Remove the temporary file after use
                break
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    retries -= 1
                    time.sleep(1)
                else:
                    raise
        if retries == 0:
            raise sqlite3.OperationalError("Database is locked after multiple attempts")
    
    return history

def predict_categories(urls):
    urls_df = pd.DataFrame(urls, columns=['URL'])
    predicted_categories = loaded_model.predict(urls_df['URL'])
    results = pd.DataFrame({'URL': urls, 'Category': predicted_categories})
    return results

@app.route('/prediction', methods=['POST'])
def predict_urls():
    data = request.json if request.is_json else request.form
    if 'urls' not in data:
        return jsonify({"error": "No 'urls' key in request data"}), 400

    urls = data['urls']
    
    if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
        return jsonify({"error": "Invalid 'urls' data format"}), 400

    predicted_results = predict_categories(urls)
    results = predicted_results.to_dict(orient='records')
    
    if request.is_json:
        # For AJAX requests
        return jsonify(results)


@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/chart')
def chat():
    return render_template('chart.html')
    
@app.route('/index')
def homes():
    return render_template('index.html')

@app.route('/results_normal')
def results_normal():
    return render_template('results_normal.html')

@app.route('/results_malicious')
def results_malicious():
    return render_template('results_malicious.html')


@app.route('/view_history', methods=['POST'])
def view_history():
    browser = request.form['browser']
    
    # Define your browser history fetching logic
    chrome_history = get_history('chrome') if browser == 'chrome' else []
    edge_history = get_history('edge') if browser == 'edge' else []
    tor_history = get_history('tor') if browser == 'tor' else []
    opera_history = get_history('opera') if browser == 'opera' else []
    brave_history = get_history('brave') if browser == 'brave' else []
    firefox_history = get_history('firefox') if browser == 'firefox' else []

    # Map browser names to their corresponding HTML files
    templates = {
        'chrome': 'chrome.html',
        'edge': 'edge.html',
        'tor': 'tor.html',
        'opera': 'opera.html',
        'brave': 'brave.html',
        'firefox': 'firefox.html'
    }

    # Render the correct template based on the browser
    return render_template(templates.get(browser, 'chrome.html'),
                           chrome_history=chrome_history,
                           edge_history=edge_history,
                           tor_history=tor_history,
                           opera_history=opera_history,
                           brave_history=brave_history,
                           firefox_history=firefox_history)


def extract_features(url):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname if parsed_url.hostname else ''
    features = {
        'length': len(url),
        'num_digits': sum(c.isdigit() for c in url),
        'num_special_chars': sum(not c.isalnum() for c in url),
        'has_https': int(parsed_url.scheme == 'https'),
        'num_subdomains': len(hostname.split('.')) - 2 if hostname else 0,
    }
    return features

@app.route('/analyze_url', methods=['POST'])
def analyze_url():
    try:
        data = request.json if request.is_json else request.form
        if 'urls' not in data:
            return jsonify({"error": "No 'urls' key in request data"}), 400

        urls = data['urls']
        if not isinstance(urls, list):
            return jsonify({"error": "'urls' should be a list"}), 400

        # Extract features using the extract_features method
        test_features = pd.DataFrame([extract_features(url) for url in urls])
        test_tfidf_features = vectorizer.transform(urls)
        test_features_sparse = csr_matrix(test_features.values)
        test_X = hstack([test_features_sparse, test_tfidf_features])
        test_predictions = model.predict(test_X)

        type_reverse_mapping = {0: 'phishing', 1: 'defacement', 2: 'malware'}
        predicted_types = [type_reverse_mapping[pred] for pred in test_predictions]

        results = [{'URL': url, 'Category': category} for url, category in zip(urls, predicted_types)]

        return jsonify(results)
    except Exception as e:
        # Log the exception with more details
        app.logger.error(f"Error processing URLs: {e}", exc_info=True)
        return jsonify({'error': f"Error processing URLs: {e}"}), 500


@app.route('/predict', methods=['POST'])
def predict():
    file = request.files.get('file')  # Use .get() to avoid KeyError
    if file:
        try:
            new_data = pd.read_csv(file)
            print(new_data)

    # Extract features from new data
            features_list = Parallel(n_jobs=-1, verbose=5)(delayed(extractfeatures)(url) for url in new_data['url'])
            features_df = pd.DataFrame(features_list)

    # Make predictions
            predictions = rfc_model.predict(features_df)
            results = []
            for url, prediction in zip(new_data['url'], predictions):
                results.append({'url': url, 'prediction': prediction})

            malicious_count = sum(predictions)
            threshold = 0.5
            malicious_proportion = malicious_count / len(predictions)

            if malicious_proportion > threshold:
                overall_result = "Malicious"
            else:
                overall_result = "Normal"

            return render_template('result.html', results=results, overall_result=overall_result)

        except Exception as e:
            return str(e)

    else:
        return "No file uploaded"


@app.route('/upload')
def upload_page():
    return render_template('upload.html')


@app.route('/send_history_for_prediction', methods=['POST'])
def send_history_for_prediction():
    browser = request.form['browser']
    history = get_history(browser)
    
    if not history:
        return "No history available for prediction", 404

    # Convert history to CSV format and save to a temporary file
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['url'])
    writer.writerows([[row[0]] for row in history])
    
    output.seek(0)
    
    # Save the CSV data to a temporary file
    temp_file_path = os.path.join(tempfile.gettempdir(), 'history.csv')
    with open(temp_file_path, 'w', newline='', encoding='utf-8') as temp_file:
        temp_file.write(output.getvalue())

    # Use requests to POST the file to the predict endpoint
    with open(temp_file_path, 'rb') as file:
        response = requests.post('http://localhost:5000/predict', files={'file': file})

    # Remove the temporary file after use
    os.remove(temp_file_path)

    # Return the response from the /predict endpoint
    return response.content






@app.route('/download_history', methods=['POST'])
def download_history():
    browser = request.form['browser']
    history = get_history(browser)
    
    if not history:
        return "No history available for download", 404

    # Extract only the URLs from the history
    urls = [[row[0]] for row in history]

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['url'])
    writer.writerows(urls)

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={browser}_history.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)
