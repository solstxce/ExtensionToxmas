from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Store active sessions and their status
active_sessions = {}

# Email configuration
EMAIL_USER = 'kvhkc2332@gmail.com'
EMAIL_PASSWORD = 'xioi npbc xhqt nfhu'

# Email Functions
def send_alert_email(parent_email, alert_type="disabled"):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = parent_email
    
    if alert_type == "disabled":
        msg['Subject'] = '🔔 Extension Status Alert: Manual Disable'
        html = '''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #e63946;">Extension Status Update</h2>
            <p style="color: #1d3557; font-size: 16px;">
                Dear Parent,
            </p>
            <p style="color: #1d3557; font-size: 16px;">
                This is to inform you that the Toxmas Parental Control extension has been manually 
                disabled using valid credentials. If this was not authorized by you, please 
                check your account security.
            </p>
            <div style="background-color: #f1faee; padding: 15px; border-left: 4px solid #e63946; margin: 20px 0;">
                <p style="margin: 0; color: #1d3557;">
                    Time of deactivation: {time}
                </p>
            </div>
        </div>
        '''.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    else:  # alert_type == "not_responding"
        msg['Subject'] = '⚠️ Extension Alert: Not Responding'
        html = '''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #e63946;">Extension Not Responding</h2>
            <p style="color: #1d3557; font-size: 16px;">
                Dear Parent,
            </p>
            <p style="color: #1d3557; font-size: 16px;">
                We've detected that the Toxmas Parental Control extension may not be functioning properly 
                or might have been disabled through browser settings. This could potentially expose 
                your child to inappropriate content.
            </p>
            <div style="background-color: #f1faee; padding: 15px; border-left: 4px solid #e63946; margin: 20px 0;">
                <p style="margin: 0; color: #1d3557;">
                    Please check your child's browser settings to ensure the extension is properly enabled.
                </p>
            </div>
        </div>
        '''

    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {str(e)}")

# Monitoring thread
def check_sessions():
    while True:
        current_time = time.time()
        to_remove = []
        
        for session_id, session in active_sessions.items():
            # Only check active sessions
            if session.get('status') != 'inactive':
                # Increase threshold to 30 seconds
                if current_time - session.get('last_ping', 0) > 30:
                    if session.get('status') != 'disabled':
                        send_alert_email(session['parent_email'], "not_responding")
                    to_remove.append(session_id)
        
        # Remove only sessions that have been inactive for more than 30 seconds
        for session_id in to_remove:
            if session_id in active_sessions:
                del active_sessions[session_id]
            
        time.sleep(5)  # Check every 5 seconds

# API Endpoints
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email')
        password = data.get('password')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        # Validate required fields
        if not all([email, password, client_id, client_secret]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Auth0 token request
        token_url = 'https://toxmas.us.auth0.com/oauth/token'
        payload = {
            'grant_type': 'password',
            'username': email,
            'password': password,
            'audience': 'https://toxmas.us.auth0.com/api/v2/',
            'scope': 'openid profile email',
            'client_id': client_id,
            'client_secret': client_secret,
            'connection': 'Username-Password-Authentication'
        }
        
        auth0_response = requests.post(token_url, json=payload)
        response_data = auth0_response.json()
        
        if auth0_response.status_code != 200:
            return jsonify(response_data), auth0_response.status_code
            
        return jsonify(response_data)
    except requests.RequestException as e:
        print('Auth0 request error:', str(e))
        return jsonify({'error': 'Authentication service unavailable'}), 503
    except Exception as e:
        print('Auth0 error:', str(e))
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/ping', methods=['POST'])
def ping():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('sessionId')
        parent_email = data.get('parentEmail')
        
        if not all([session_id, parent_email]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create or update session
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                'parent_email': parent_email,
                'status': 'enabled',
                'created_at': time.time()
            }
        
        # Always update last_ping
        active_sessions[session_id].update({
            'last_ping': time.time(),
            'parent_email': parent_email
        })
        
        return jsonify({
            'status': active_sessions[session_id].get('status', 'enabled'),
            'message': 'Ping successful'
        }), 200
    except Exception as e:
        print('Ping error:', str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/toggle-extension', methods=['POST'])
def toggle_extension():
    print("Received toggle-extension request")
    try:
        data = request.json
        print(f"Request data: {data}")
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('sessionId')
        parent_email = data.get('parentEmail')
        new_status = data.get('status')
        
        print(f"Processing request for session: {session_id}")
        
        if not all([session_id, parent_email, new_status]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        if new_status not in ['enabled', 'disabled']:
            return jsonify({'error': 'Invalid status value'}), 400
        
        if session_id in active_sessions:
            active_sessions[session_id]['status'] = new_status
            if new_status == 'disabled':
                send_alert_email(parent_email, "disabled")
            
            return jsonify({
                'status': new_status,
                'message': f'Extension {new_status} successfully'
            }), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        print(f'Toggle error: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/logout', methods=['POST'])
def logout():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('sessionId')
        if not session_id:
            return jsonify({'error': 'Missing session ID'}), 400
        
        # Instead of deleting, mark session as inactive
        if session_id in active_sessions:
            active_sessions[session_id]['status'] = 'inactive'
            return jsonify({
                'status': 'success',
                'message': 'Session marked as inactive'
            }), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        print('Logout error:', str(e))
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting server...")
    monitoring_thread = threading.Thread(target=check_sessions, daemon=True)
    monitoring_thread.start()
    print("Monitoring thread started...")
    app.run(port=3000, debug=True, host='0.0.0.0') 