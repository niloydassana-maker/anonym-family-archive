import requests
import json

ACCOUNT_SID = "AC0df25d3d89c42672d99f71501b0bda10"
AUTH_TOKEN = "d8a70dcdf44b79d35c4ff9ef2366221c"
auth = (ACCOUNT_SID, AUTH_TOKEN)
VOICE_URL = "https://kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run/twilio/voice"

print("=" * 60)
print("CONFIGURING BACKUP TWILIO NUMBER & DIALING PERMISSIONS")
print("=" * 60)

# 1. Fetch and configure incoming phone number
res = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/IncomingPhoneNumbers.json", auth=auth)
nums = res.json().get("incoming_phone_numbers", [])
print(f"Found {len(nums)} incoming numbers.")

for n in nums:
    pn = n.get("phone_number")
    sid = n.get("sid")
    print(f"Configuring {pn} ({sid}) -> VoiceUrl: {VOICE_URL}")
    update_res = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/IncomingPhoneNumbers/{sid}.json",
        auth=auth,
        data={
            "VoiceUrl": VOICE_URL,
            "VoiceMethod": "POST",
            "FriendlyName": "SugarDoctor Hindi Voice Clinic (Backup)"
        }
    )
    print("  Update status:", update_res.status_code)
    print("  Configured VoiceUrl:", update_res.json().get("voice_url"))

# 2. Check and enable India (IN) Voice Dialing Permissions
in_perm_url = "https://voice.twilio.com/v1/DialingPermissions/Countries/IN"
perm_res = requests.get(in_perm_url, auth=auth)
print("\nIndia Dialing Permission status:", perm_res.status_code)
perm_data = perm_res.json()
print("  Low risk numbers enabled:", perm_data.get("low_risk_numbers_enabled"))

if not perm_data.get("low_risk_numbers_enabled"):
    print("Enabling India Voice Dialing Permissions...")
    payload = json.dumps([{
        "iso_code": "IN",
        "low_risk_numbers_enabled": True,
        "high_risk_special_numbers_enabled": False,
        "high_risk_tollfraud_numbers_enabled": False
    }])
    patch_res = requests.post(
        "https://voice.twilio.com/v1/DialingPermissions/BulkCountryUpdates",
        auth=auth,
        data={"UpdateRequest": payload}
    )
    print("  Bulk update result:", patch_res.status_code)
    
    # Re-verify
    re_res = requests.get(in_perm_url, auth=auth)
    print("  Re-verified low risk enabled:", re_res.json().get("low_risk_numbers_enabled"))
else:
    print("  India low-risk dialing is ALREADY enabled!")

# 3. Check Balance / Trial Credits
bal_res = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Balance.json", auth=auth)
print("\nBalance Info:", bal_res.json())

# 4. Check Verified Caller IDs
caller_res = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/OutgoingCallerIds.json", auth=auth)
callers = caller_res.json().get("outgoing_caller_ids", [])
print(f"\nVerified Caller IDs ({len(callers)}):")
for c in callers:
    print(f"  {c.get('phone_number')} - {c.get('friendly_name')}")

print("\nBackup Twilio Account 100% Configured and Ready!")
