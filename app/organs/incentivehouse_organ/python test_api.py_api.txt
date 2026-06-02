import urllib.request
import json

BASE = 'http://127.0.0.1:9001'

def post(url, data=None):
    req = urllib.request.Request(url, method='POST')
    req.add_header('Content-Type', 'application/json')
    if data:
        req.data = json.dumps(data).encode('utf-8')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode('utf-8'))

print('=== AUTH ===')
auth = post(f'{BASE}/v2/auth/login', {'username':'admin','password':'admin123'})
token = auth['access_token']
print(f'Token: {token[:40]}...')

print('\n=== EXTRACT BNK ===')
result = post(f'{BASE}/v2/extract?token={token}', {'module':'BNK','source_file':'Bnk_TRNX SOURCE.xlsx','dry_run':False})
print(f'Status: {result.get("status")}')
print(f'Read: {result.get("records_read")}')
print(f'Inserted: {result.get("records_inserted")}')
print(f'Errors: {result.get("errors", [])}')

print('\n=== EXTRACT MASTER ===')
result = post(f'{BASE}/v2/extract/master?token={token}')
print(f'Status: {result.get("status")}')
print(f'Tables: {result.get("tables_processed")}')
print(f'Records: {result.get("records_inserted")}')

print('\n=== STATUS ===')
result = get(f'{BASE}/v2/status?token={token}')
print(f'Tables: {len(result.get("records", {}))}')
for name, count in sorted(result.get('records', {}).items()):
    print(f'  {name}: {count}')

print('\n=== HEALTH ===')
print(get(f'{BASE}/health'))

print('\n=== DONE ===')