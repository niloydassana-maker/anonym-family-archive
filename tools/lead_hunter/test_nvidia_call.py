import requests
import json
import time

key = open("D:/anonym/vault/nvidia_key_clinic_brain.txt").read().strip()
url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# Fetch models list
r = requests.get("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {key}"})
all_models = [m["id"] for m in r.json().get("data", [])]

print(f"Testing models against account to find authorized ones...")
authorized = []
for m in all_models:
    try:
        res = requests.post(url, headers=headers, json={
            "model": m,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5
        }, timeout=8)
        if res.status_code == 200:
            print(f"  [200 OK] {m}")
            authorized.append(m)
        elif res.status_code != 404:
            print(f"  [{res.status_code}] {m} -> {res.text[:60]}")
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {m}")
    except Exception as e:
        pass

print("\nAuthorized live models for this account:", authorized)
