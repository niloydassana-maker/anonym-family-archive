import os, json

with open(r'C:\Users\Admin\.kaggle\kaggle.json') as f:
    creds = json.load(f)
os.environ['KAGGLE_USERNAME'] = creds['username']
os.environ['KAGGLE_KEY'] = creds['key']

from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
logs = api.kernels_output('isearchxsolve', 'kilo-xtts-tune')
with open(r'D:\anonym\xtts_logs_full.txt', 'w', encoding='utf-8') as f:
    f.write(logs)
print(logs[:5000])