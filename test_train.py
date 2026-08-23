import requests, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')

r = requests.post('http://localhost:8000/api/v1/auth/login', json={'email':'admin@mlpipeline.com','password':'admin123'}, timeout=10)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# 1. Find an existing dataset
print("=== Step 1: Find dataset ===")
r_datasets = requests.get('http://localhost:8000/api/v1/datasets', headers=h, timeout=10)
datasets = r_datasets.json()
if isinstance(datasets, dict):
    datasets = datasets.get('items', [])
print(f"Found {len(datasets)} datasets")
for ds in datasets:
    print(f"  - {ds.get('name')} ({ds.get('id')})")

# Find one with numeric data
ds_id = None
for ds in datasets:
    if ds.get('name') and 'data' in ds.get('name', '').lower():
        ds_id = ds.get('id')
        ds_name = ds.get('name')
        break
if not ds_id and datasets:
    ds_id = datasets[0].get('id')
    ds_name = datasets[0].get('name')
print(f"Using dataset: {ds_name} ({ds_id})")

if not ds_id:
    print("No datasets found!")
    sys.exit(1)

# 2. Auto-analyze
print("\n=== Step 2: Auto-analyze ===")
r2 = requests.post('http://localhost:8000/api/v1/models/auto-analyze', headers=h, json={
    'dataset_id': ds_id
}, timeout=30)
print('Status:', r2.status_code)
if r2.status_code != 200:
    print(r2.text[:300])
    sys.exit(1)
analysis = r2.json()
print(f"Target: {analysis['suggested_target']} ({analysis['target_reason']})")
print(f"Algorithm: {analysis['suggested_algorithm']}")
print(f"Problem: {analysis['problem_type']}")
print(f"Columns: {len(analysis['column_summaries'])}")
for col in analysis['column_summaries'][:5]:
    print(f"  - {col['name']}: {col['dtype']} ({col['role']})")
if '_sheet_name' in [c['name'] for c in analysis['column_summaries']]:
    print("WARNING: _sheet_name still in column summaries!")

# 3. Create model
print("\n=== Step 3: Create model ===")
r3 = requests.post('http://localhost:8000/api/v1/models', headers=h, json={
    'name': 'Auto-verify-test',
    'algorithm': analysis['suggested_algorithm'],
    'target_column': analysis['suggested_target'],
}, timeout=15)
print('Status:', r3.status_code)
model_id = r3.json()['id']
print(f"Model ID: {model_id}")

# 4. Train (sync)
print("\n=== Step 4: Train ===")
t0 = time.time()
r4 = requests.post(f'http://localhost:8000/api/v1/models/{model_id}/train', headers=h, json={
    'dataset_id': ds_id,
    'algorithm': analysis['suggested_algorithm'],
    'target_column': analysis['suggested_target'],
    'async_training': False,
    'mode': 'simple',
    'problem_type': analysis['problem_type'],
}, timeout=120)
elapsed = time.time() - t0
print(f'Train: {r4.status_code} ({elapsed:.1f}s)')
if r4.status_code != 200:
    print(r4.text[:500])
    sys.exit(1)
train_data = r4.json()
print(f"Status: {train_data.get('status')}")
print(f"Experiment ID: {train_data.get('experiment_id')}")

# 5. Verify model saved correctly
print("\n=== Step 5: Verify model ===")
r5 = requests.get(f'http://localhost:8000/api/v1/models/{model_id}', headers=h, timeout=10)
print(f'GET model: {r5.status_code}')
if r5.status_code == 200:
    m = r5.json()
    print(f"  status: {m.get('status')}")
    print(f"  file_path: {m.get('file_path')}")
    print(f"  feature_names: {len(m.get('feature_names', []))} features")
    fn = m.get('feature_names', [])
    if fn:
        print(f"  features: {fn[:5]}{'...' if len(fn) > 5 else ''}")
    print(f"  metrics: {json.dumps(m.get('metrics', {}), indent=2)[:200]}")
    print(f"  target_column: {m.get('target_column')}")
else:
    print(r5.text[:300])

print("\n=== DONE ===")
