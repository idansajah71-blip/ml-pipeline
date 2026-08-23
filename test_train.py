import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

r = requests.post('http://localhost:8000/api/v1/auth/login', json={'email':'admin@mlpipeline.com','password':'admin123'}, timeout=10)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# 1. Auto-analyze
print("=== Step 1: Auto-analyze ===")
with open('datasets/sample_classification.csv', 'rb') as f:
    r1 = requests.post('http://localhost:8000/api/v1/models/auto-analyze',
        headers=h, files={'file': ('data.csv', f)}, timeout=30)
print('Analyze:', r1.status_code)
if r1.status_code != 200:
    print(r1.text[:300])
    sys.exit(1)
analysis = r1.json()
print('Columns:', [c['name'] for c in analysis['column_summaries']])
print('Target:', analysis.get('suggested_target'))
print('Algorithm:', analysis.get('suggested_algorithm'))
print('Problem type:', analysis.get('problem_type'))

# 2. Create model
print("\n=== Step 2: Create model ===")
r2 = requests.post('http://localhost:8000/api/v1/models', headers=h, json={
    'name': 'Auto-test',
    'algorithm': analysis['suggested_algorithm'],
    'target_column': analysis['suggested_target'],
}, timeout=15)
print('Create:', r2.status_code)
if r2.status_code != 201:
    print(r2.text[:300])
    sys.exit(1)
model_id = r2.json()['id']
print('Model ID:', model_id)

# 3. Train (sync)
print("\n=== Step 3: Train ===")
r3 = requests.post(f'http://localhost:8000/api/v1/models/{model_id}/train', headers=h, json={
    'dataset_id': state_dataset_id,
    'algorithm': analysis['suggested_algorithm'],
    'target_column': analysis['suggested_target'],
    'async_training': False,
    'mode': 'simple',
    'problem_type': analysis['problem_type'],
}, timeout=120)
print('Train:', r3.status_code)
if r3.status_code == 200:
    train_result = r3.json()
    print('Status:', train_result.get('status'))
    print('Experiment ID:', train_result.get('experiment_id'))
    
    # 4. Get experiment
    exp_id = train_result.get('experiment_id')
    if exp_id:
        r4 = requests.get(f'http://localhost:8000/api/v1/experiments/{exp_id}', headers=h, timeout=10)
        print('Experiment:', r4.status_code)
        if r4.status_code == 200:
            exp = r4.json()
            print('Results:', exp.get('results', {}))
else:
    print(r3.text[:300])
