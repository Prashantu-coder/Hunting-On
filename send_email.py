import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# === CONFIGURATION ===
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1_pmG2oMSEk8VciNm2uqcshyvPPZBbjf-oKV59chgT1w/export?format=csv&gid=0"
DAYS_LOOKBACK = 1  # Change to 7 for weekly signals
EMAIL_SENDER = "prashantstha0912@gmail.com"
EMAIL_PASSWORD = "dbyl roef onlg afaj"
EMAIL_RECEIVER = "prashantshrestha473@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def fetch_data():
    df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
    df.columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['tag'] = df.get('tag', '')  # ensure tag column exists
    return df


def filter_signals(df):
    recent_date = df['date'].max()
    since = recent_date - timedelta(days=DAYS_LOOKBACK)
    signals = df[(df['date'] >= since) & (df['tag'] != '')]
    return signals[['date', 'symbol', 'close', 'tag']].sort_values('date', ascending=False)


def send_email(signal_df):
    if signal_df.empty:
        print("No signals to send.")
        return

    body = signal_df.to_string(index=False)
    msg = MIMEText(body)
    msg["Subject"] = f"🔔 Detected Trading Signals - Last {DAYS_LOOKBACK} Day(s)"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


if __name__ == "__main__":
    data = fetch_data()
    signal_data = filter_signals(data)
    send_email(signal_data)
