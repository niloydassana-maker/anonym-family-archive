import requests
import json

# Backup Twilio Account 2 (with kunal-colab Modal backend)
ACCOUNT_SID = "AC0df25d3d89c42672d99f71501b0bda10"
AUTH_TOKEN = "d8a70dcdf44b79d35c4ff9ef2366221c"
FROM_NUMBER = "+15167581277"
TO_NUMBER = "+918617216163"  # Verified iQOO Phone on Account 2

TWILIO_VOICE_URL = "https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/twilio/voice"

url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Calls.json"

payload = {
    "To": TO_NUMBER,
    "From": FROM_NUMBER,
    "Url": TWILIO_VOICE_URL,
    "Method": "POST"
}

print(f"Triggering outbound call from {FROM_NUMBER} to {TO_NUMBER} via {TWILIO_VOICE_URL}...")
res = requests.post(url, auth=(ACCOUNT_SID, AUTH_TOKEN), data=payload)
print("Response HTTP Status:", res.status_code)
try:
    data = res.json()
    print("Call SID:", data.get("sid"))
    print("Call Status:", data.get("status"))
    print("Direction:", data.get("direction"))
except Exception:
    print("Response text:", res.text)
