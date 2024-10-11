
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid
from flask import Flask, request, send_file, redirect, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from urllib.parse import urlparse
import json
from user_agents import parse
import plotly.graph_objs as go
import plotly
from flask_cors import CORS


# import from environment variables
smtp_host = os.getenv('SMTP_HOST')
smtp_port = os.getenv('SMTP_PORT')
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')

# Flask app setup
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///email_metrics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

msg_from = smtp_username
msg_from_pw = smtp_password
mailing_list = ["b.alp.kocak@gmail.com", "ilker.07yoru@gmail.com"]
msg_subject = "Application Received - Bosch HR"

# Database model
class EmailMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    tracking_id = db.Column(db.String(36), unique=True, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    opened = db.Column(db.Boolean, default=False)
    opened_at = db.Column(db.DateTime)
    open_count = db.Column(db.Integer, default=0)
    button_clicked = db.Column(db.Boolean, default=False)
    button_clicked_at = db.Column(db.DateTime)
    click_count = db.Column(db.Integer, default=0)
    user_agent = db.Column(db.String(200))
    ip_address = db.Column(db.String(45))
    device_type = db.Column(db.String(20))
    os = db.Column(db.String(50))
    browser = db.Column(db.String(50))
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    engagement_time = db.Column(db.Integer, default=0)  # in seconds

def create_app():
    with app.app_context():
        db.create_all()
    return app

def generate_tracking_pixel(tracking_id):
    return f'<img src="http://localhost:5001/track/{tracking_id}" width="1" height="1" />'

def generate_tracking_link(tracking_id, original_link):
    return f'http://localhost:5001/click/{tracking_id}?url={original_link}'

def create_html_content(tracking_id):
    tracking_pixel = generate_tracking_pixel(tracking_id)
    tracked_button_link = generate_tracking_link(tracking_id, "https://www.example.com/candidate-portal")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Application Received - Bosch HR</title>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
        body {{
          font-family: 'Roboto', Arial, sans-serif;
          line-height: 1.6;
          color: #333;
          margin: 0;
          padding: 0;
          background-color: #f4f4f4;
        }}
        .container {{
          max-width: 600px;
          margin: 20px auto;
          background-color: #ffffff;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
        }}
        .header {{
          background-color: #005691;
          color: #ffffff;
          text-align: center;
          padding: 20px;
        }}
        .logo {{
          width: 150px;
          height: auto;
        }}
        .content {{
          padding: 30px;
        }}
        h1 {{
          color: #005691;
          margin-top: 0;
        }}
        .cta-button {{
          display: inline-block;
          background-color: #e20015;
          color: #ffffff;
          padding: 12px 24px;
          text-decoration: none;
          border-radius: 4px;
          font-weight: bold;
          transition: background-color 0.3s ease;
        }}
        .cta-button:hover {{
          background-color: #b1000f;
        }}
        .footer {{
          background-color: #005691;
          color: #ffffff;
          text-align: center;
          padding: 10px;
          font-size: 12px;
        }}
      </style>
    </head>
    <body>
      {tracking_pixel}
      <div class="container">
        <div class="header">
          <img src="https://www.bosch.com/assets/img/bosch-logo.png" alt="Bosch Logo" class="logo">
        </div>
        <div class="content">
          <h1>Application Received</h1>
          <p>Dear Applicant,</p>
          <p>Thank you for applying for the position of <strong>Software Engineer</strong> at Bosch. We have successfully received your application and are excited to review it.</p>
          <p>Our hiring team will carefully review your application and get back to you as soon as possible regarding the next steps in the process.</p>
          <p>You can check the status of your application through our candidate portal:</p>
          <p style="text-align: center;">
            <a href="{tracked_button_link}" class="cta-button">Check Application Status</a>
          </p>
          <p>If you have any questions, please don't hesitate to contact our HR department at <a href="mailto:hr@bosch.com">hr@bosch.com</a>.</p>
          <p>
            Best regards,<br>
            Bosch HR Team
          </p>
        </div>
        <div class="footer">
          <p>© {datetime.now().year} Robert Bosch GmbH. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """
    return html_content

def send_email(recipient):
    tracking_id = str(uuid.uuid4())
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = msg_subject
    msg['From'] = msg_from
    msg['To'] = recipient

    text_content = "This is a fallback plain text message. Please view this email with an HTML-capable email client."
    html_content = create_html_content(tracking_id)
    
    part1 = MIMEText(text_content, 'plain')
    part2 = MIMEText(html_content, 'html')
    msg.attach(part1)
    msg.attach(part2)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(msg_from, msg_from_pw)
            server.send_message(msg)
        print(f"Email sent successfully to {recipient}")
        
        # Save initial metric
        with app.app_context():
            new_metric = EmailMetrics(email=recipient, tracking_id=tracking_id)
            db.session.add(new_metric)
            db.session.commit()
    except Exception as e:
        print(f"Failed to send email to {recipient}. Error: {str(e)}")

def get_user_info(user_agent_string):
    user_agent = parse(user_agent_string)
    return {
        'device_type': user_agent.device.family,
        'os': user_agent.os.family,
        'browser': user_agent.browser.family
    }

@app.route('/track/<tracking_id>')
def track_open(tracking_id):
    with app.app_context():
        metric = EmailMetrics.query.filter_by(tracking_id=tracking_id).first()
        if metric:
            if not metric.opened:
                metric.opened = True
                metric.opened_at = datetime.utcnow()
            metric.open_count += 1
            user_agent_string = request.headers.get('User-Agent')
            user_info = get_user_info(user_agent_string)
            metric.user_agent = user_agent_string
            metric.ip_address = request.remote_addr
            metric.device_type = user_info['device_type']
            metric.os = user_info['os']
            metric.browser = user_info['browser']
            metric.country = "Unknown"  # Gerçek uygulamada bir geolocation servisi kullanılmalı
            metric.city = "Unknown"
            db.session.commit()
    return send_file('Pixel-1x1.png', mimetype='image/png')

@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    with app.app_context():
        metric = EmailMetrics.query.filter_by(tracking_id=tracking_id).first()
        if metric:
            if not metric.opened:
                # E-posta açılmamışsa, açılmış olarak işaretle
                metric.opened = True
                metric.opened_at = datetime.utcnow()
                metric.open_count += 1
            metric.button_clicked = True
            metric.click_count += 1
            if not metric.button_clicked_at:
                metric.button_clicked_at = datetime.utcnow()
            user_agent_string = request.headers.get('User-Agent')
            user_info = get_user_info(user_agent_string)
            metric.user_agent = user_agent_string
            metric.ip_address = request.remote_addr
            metric.device_type = user_info['device_type']
            metric.os = user_info['os']
            metric.browser = user_info['browser']
            metric.country = "Unknown"  # Gerçek uygulamada bir geolocation servisi kullanılmalı
            metric.city = "Unknown"
            db.session.commit()
    return redirect(request.args.get('url'))

@app.route('/metrics')
def view_metrics():
    with app.app_context():
        metrics = EmailMetrics.query.all()
        output = []
        for metric in metrics:
            output.append({
                'email': metric.email,
                'sent_at': metric.sent_at.isoformat(),
                'opened': metric.opened,
                'opened_at': metric.opened_at.isoformat() if metric.opened_at else None,
                'open_count': metric.open_count,
                'button_clicked': metric.button_clicked,
                'button_clicked_at': metric.button_clicked_at.isoformat() if metric.button_clicked_at else None,
                'click_count': metric.click_count,
                'user_agent': metric.user_agent,
                'ip_address': metric.ip_address,
                'device_type': metric.device_type,
                'os': metric.os,
                'browser': metric.browser,
                'country': metric.country,
                'city': metric.city,
                'engagement_time': metric.engagement_time
            })
    return jsonify({'metrics': output})

@app.route('/dashboard')
def dashboard():
    with app.app_context():
        metrics = EmailMetrics.query.all()
        
        # Prepare data for charts
        total_sent = len(metrics)
        total_opened = sum(1 for m in metrics if m.opened)
        total_clicked = sum(1 for m in metrics if m.button_clicked)
        
        device_types = [m.device_type for m in metrics if m.opened]
        device_type_counts = {device: device_types.count(device) for device in set(device_types)}
        
        # Create charts
        open_rate_chart = go.Pie(labels=['Opened', 'Not Opened'], values=[total_opened, total_sent - total_opened])
        click_rate_chart = go.Pie(labels=['Clicked', 'Not Clicked'], values=[total_clicked, total_sent - total_clicked])
        device_type_chart = go.Bar(x=list(device_type_counts.keys()), y=list(device_type_counts.values()))
        
        # Convert charts to JSON
        open_rate_json = json.dumps(open_rate_chart, cls=plotly.utils.PlotlyJSONEncoder)
        click_rate_json = json.dumps(click_rate_chart, cls=plotly.utils.PlotlyJSONEncoder)
        device_type_json = json.dumps(device_type_chart, cls=plotly.utils.PlotlyJSONEncoder)
        
        # Render dashboard template
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Metrics Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f0f0f0;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                }
                .chart {
                    margin-bottom: 30px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Email Metrics Dashboard</h1>
                <div class="chart">
                    <h2>Open Rate</h2>
                    <div id="openRateChart"></div>
                </div>
                <div class="chart">
                    <h2>Click Rate</h2>
                    <div id="clickRateChart"></div>
                </div>
                <div class="chart">
                    <h2>Device Types</h2>
                    <div id="deviceTypeChart"></div>
                </div>
            </div>
            <script>
                var openRateData = {{ open_rate_json | safe }};
                var clickRateData = {{ click_rate_json | safe }};
                var deviceTypeData = {{ device_type_json | safe }};
                
                Plotly.newPlot('clickRateChart', [clickRateData], {height: 400, width: 400});
                Plotly.newPlot('deviceTypeChart', [deviceTypeData], {height: 400, width: 600});
            </script>
        </body>
        </html>
        """, open_rate_json=open_rate_json, click_rate_json=click_rate_json, device_type_json=device_type_json)

def pretty_print_logs():
    with app.app_context():
        metrics = EmailMetrics.query.all()
        for metric in metrics:
            print(json.dumps({
                'email': metric.email,
                'sent_at': metric.sent_at.isoformat(),
                'opened': metric.opened,
                'opened_at': metric.opened_at.isoformat() if metric.opened_at else None,
                'open_count': metric.open_count,
                'button_clicked': metric.button_clicked,
                'button_clicked_at': metric.button_clicked_at.isoformat() if metric.button_clicked_at else None,
                'click_count': metric.click_count,
                'device_type': metric.device_type,
                'os': metric.os,
                'browser': metric.browser,
                'country': metric.country,
                'city': metric.city,
                'engagement_time': metric.engagement_time
            }, indent=2))
            print('-' * 50)

@app.route('/engagement/<tracking_id>', methods=['POST'])
def track_engagement(tracking_id):
    engagement_time = request.json.get('engagement_time', 0)
    with app.app_context():
        metric = EmailMetrics.query.filter_by(tracking_id=tracking_id).first()
        if metric:
            metric.engagement_time += engagement_time
            db.session.commit()
    return jsonify({'status': 'success'})

def main():
    for recipient in mailing_list:
        send_email(recipient)
    pretty_print_logs()

if __name__ == '__main__':
    create_app()
    main()
    app.run(debug=True, host='0.0.0.0', port=5001)