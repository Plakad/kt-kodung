import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import logging
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize logger
logging.basicConfig(level=logging.INFO)

# Get sensitive information from environment variables
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

# Initialize Line Bot API and Webhook Handler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Authenticate with Google Sheets
credentials_info = {
    "type": "service_account",
    "project_id": os.getenv("project_id"),
    "private_key_id": os.getenv("private_key_id"),
    "private_key": os.getenv("private_key").replace("\\n", "\n"),  # Ensure proper newline formatting
    "client_email": os.getenv("client_email"),
    "client_id": os.getenv("client_id"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("client_x509_cert_url")
}

# Create Google Sheets credentials object
google_creds = Credentials.from_service_account_info(credentials_info)

# Authorize the client to interact with Google Sheets
client = gspread.authorize(google_creds)

# Open the Google Sheet
sheet = client.open("line-chat-bot-score").sheet1

# Read the Google Sheet into a pandas DataFrame
data = sheet.get_all_values()  # Get all values as a list of lists
headers = data[0]  # Assume the first row is the header
df = pd.DataFrame(data[1:], columns=headers)  # Create DataFrame from data

@app.route("/")
def home():
    return "Welcome to Kanpot [Kodung] Line Chat Bot! V.2 "

@app.route("/callback", methods=['POST'])
def callback():
    # Get request header signature
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# Function to get score based on user ID
def get_score(user_id):
    user_score = df[df['User ID'] == user_id]  # Assuming 'User ID' is the name of the column
    if not user_score.empty:
        return user_score['Score'].values[0]  # Return the score
    return None  # Return None if user ID is not found

def get_name(user_id):
    user_name = df[df['User ID'] == user_id]
    if not user_name.empty:
        return user_name['Name'].values[0]  # Return Name
    return None  # Return None if user ID is not found

# Define what happens when the bot receives a message
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.message.text.strip()  # Get user input, assuming it's their ID
    
    # Fetch the score and name from Google Sheets using the ID
    score = get_score(user_id)
    name = get_name(user_id)
    
    if score is not None:
        # If the score exists, reply with the user's score
        reply = f"Hello {name}, Your score is: {score}"
    else:
        # If the ID was not found, reply with a message
        reply = "ID not found or no score available."

    # Send the reply to the user
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(port=10000)  # Change port if needed for Render
