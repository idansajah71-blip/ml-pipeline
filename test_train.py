import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

r = requests.post('http://localhost:8000/api/v1/auth/login', json={'email':'admin@mlpipeline.com','password':'admin123'}, timeout=10)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# Create model
r2 = requests.post('http://localhost:8000/api/v1/models', headers=h, json={
    'name': 'Test Train', 'algorithm': 'random_forest', 'target_column': 'status',
}, timeout=15)
mid = r2.json()['id']
print(f'Model created: {mid}')

# Train
t0 = time.time()
r3 = requests.post(f'http://localhost:8000/api/v1/models/{mid}/train', headers=h, json={
    'dataset_id': '696632fc-4fed-40f8-acac-757c1fb0fe8b',
    'algorithm': 'random_forest',
    'target_column': 'status',
    'async_training': False,
    'mode': 'simple',
    'problem_type': 'classification',
}, timeout=120)
elapsed = time.time() - t0
print(f'Train: {r3.status_code} ({elapsed:.1f}s)')
if r3.status_code == 200:
    data = r3.json()
    print(f'Status: {data.get("status")}')
    print(f'Metrics: {data.get("metrics", {})}')
else:
    print(r3.text[:500])
