import requests
import json

ACCOUNT_SID = "ACac1991bfb3b63cc9095e36a2d69b1de7"
AUTH_TOKEN = "aa2737391d601abacc2dced8731b97d1"
FROM_NUMBER = "+12792443149"
TO_NUMBER = "+918617216163"  # Baba's iQOO Z7 Pro!

TWILIO_VOICE_URL = "https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/twilio/voice"

url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Calls.json"

payload = {
    "To": TO_NUMBER,
    "From": FROM_NUMBER,
    "Url": TWILIO_VOICE_URL,
    "Method": "POST"
}

print(f"Triggering outbound call from {FROM_NUMBER} to iQOO {TO_NUMBER}...")
res = requests.post(url, auth=(ACCOUNT_SID, AUTH_TOKEN), data=payload)
print("Response HTTP Status:", res.status_code)
try:
    data = res.json()
    print("Call SID:", data.get("sid"))
    print("Call Status:", data.get("status"))
    print("Direction:", data.get("direction"))
except Exception:
    print("Response text:", res.text)
