import json
import uuid
import requests
from app.core.config import get_settings

BASE = 'http://127.0.0.1:8000'


def fail(step, detail, evidence=None):
    print('GO LIVE FAILED')
    print(f'{step}={detail}')
    if evidence is not None:
        print(f'EVIDENCE={evidence}')
    raise SystemExit(1)

# Pre-check health
r = requests.get(f'{BASE}/api/v1/health', timeout=20)
if r.status_code != 200:
    fail('STEP_PRECHECK_HEALTH', f'FAIL({r.status_code})', r.text)
print('STEP_PRECHECK_HEALTH=PASS')

# Pre-check settings key
if not bool(get_settings().openai_api_key):
    fail('STEP_PRECHECK_SETTINGS_KEY', 'FAIL')
print('STEP_PRECHECK_SETTINGS_KEY=PASS')

# Pre-check upstream one real request
payload = {
    'model': 'gpt-4o-mini',
    'temperature': 0,
    'max_tokens': 120,
    'messages': [
        {'role': 'system', 'content': 'Return only JSON.'},
        {'role': 'user', 'content': 'Return valid JSON only with keys hook and hashtags. Values must be non-empty strings.'},
    ],
}
up = requests.post(
    'https://api.openai.com/v1/chat/completions',
    headers={'Authorization': f'Bearer {get_settings().openai_api_key}'},
    json=payload,
    timeout=30,
)
if up.status_code in {401, 403, 429, 500, 503}:
    fail('STEP_PRECHECK_UPSTREAM', f'FAIL({up.status_code})', up.text)
if up.status_code != 200:
    fail('STEP_PRECHECK_UPSTREAM', f'FAIL({up.status_code})', up.text)
print('STEP_PRECHECK_UPSTREAM=PASS')

# Login
with open('.tmp_ai_user_login.json', 'r', encoding='ascii') as f:
    login_payload = json.load(f)
login = requests.post(f'{BASE}/api/v1/auth/login', json=login_payload, timeout=20)
if login.status_code != 200:
    fail('STEP_LOGIN', f'FAIL({login.status_code})', login.text)
token = login.json().get('access_token')
if not token:
    fail('STEP_LOGIN', 'FAIL(NO_TOKEN)')
headers = {'Authorization': f'Bearer {token}'}
print('STEP_LOGIN=PASS')

# Import
imp_payload = {'url': 'https://shopee.co.id/product/1/6203?release=rc1-cert-fix'}
imp = requests.post(f'{BASE}/api/v1/products/import', headers=headers, json=imp_payload, timeout=20)
if imp.status_code != 201:
    fail('STEP_IMPORT', f'FAIL({imp.status_code})', imp.text)
product_id = imp.json()['id']
print(f'STEP_IMPORT=PASS product_id={product_id}')

# Generate NEW content via app parser path
req = {
    'product_id': product_id,
    'platform': 'facebook',
    'content_types': ['hook', 'hashtags'],
    'style': 'professional',
    'target_audience': 'students',
    'language': 'id',
    'provider': 'openai',
    'model': 'gpt-4o-mini',
}
gen = requests.post(f'{BASE}/api/v1/ai/generate', headers=headers, json=req, timeout=60)
if gen.status_code != 200:
    fail('STEP_GENERATE', f'FAIL({gen.status_code})', gen.text)
gen_json = gen.json()
content_id = gen_json.get('content_id')
generated_text = gen_json.get('generated_text') or {}
if not isinstance(generated_text, dict) or not generated_text.get('hook') or not generated_text.get('hashtags'):
    fail('STEP_GENERATE', 'FAIL(MISSING_HOOK_OR_HASHTAGS)', gen.text)
print(f'STEP_GENERATE=PASS content_id={content_id}')
print('VERIFY_PARSED_KEYS=PASS hook,hashtags')

# History contains content_id
hist = requests.get(f'{BASE}/api/v1/ai/history', headers=headers, params={'limit': 20, 'offset': 0, 'product_id': product_id}, timeout=20)
if hist.status_code != 200:
    fail('STEP_HISTORY', f'FAIL({hist.status_code})', hist.text)
items = hist.json().get('items', [])
if not any(int(item.get('id', -1)) == int(content_id) for item in items):
    fail('STEP_HISTORY', f'FAIL(MISSING_CONTENT_ID={content_id})')
print('STEP_HISTORY=PASS')

# Publish with NEW content
accounts = requests.get(f'{BASE}/api/v1/social/accounts', headers=headers, timeout=20)
if accounts.status_code != 200:
    fail('STEP_SOCIAL_ACCOUNTS', f'FAIL({accounts.status_code})', accounts.text)
acc_list = accounts.json()
if acc_list:
    social_id = acc_list[0]['id']
else:
    create_acc = {
        'platform': 'facebook',
        'account_name': 'RC1 FB',
        'account_identifier': 'fb_rc1_fix',
        'permissions': ['publish_posts'],
        'timezone': 'UTC',
        'business_hours_start': 8,
        'business_hours_end': 20,
        'rate_limit_per_minute': 120,
        'access_token': 'token',
        'refresh_token': 'refresh',
        'token_expires_at': None,
        'scopes': ['publish'],
    }
    c = requests.post(f'{BASE}/api/v1/social/accounts', headers=headers, json=create_acc, timeout=20)
    if c.status_code != 201:
        fail('STEP_SOCIAL_CREATE', f'FAIL({c.status_code})', c.text)
    social_id = c.json()['id']

publish_payload = {
    'social_account_id': social_id,
    'product_id': product_id,
    'post_type': 'facebook_feed',
    'caption_content_id': content_id,
    'media_attachments': ['https://cdn.example.com/rc1.jpg'],
    'mentions': [],
    'hashtags': ['#rc1'],
    'cta': 'Buy now',
    'affiliate_link': 'https://example.com/aff',
    'alt_text': 'rc1',
    'idempotency_key': str(uuid.uuid4()),
}
pub = requests.post(f'{BASE}/api/v1/publish', headers=headers, json=publish_payload, timeout=30)
if pub.status_code != 200:
    fail('STEP_PUBLISH', f'FAIL({pub.status_code})', pub.text)
pub_json = pub.json()
job = pub_json.get('job') or {}
if job.get('status') != 'published':
    fail('STEP_PUBLISH', 'FAIL(NOT_PUBLISHED)', pub.text)
print(f"STEP_PUBLISH=PASS job_id={job.get('id')} status={job.get('status')}")

print('GO LIVE STATUS READY')
print('Release Candidate v1.0.0-rc1')
print('APPROVED FOR PRODUCTION')
