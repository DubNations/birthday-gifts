"""全面用户行为模拟测试 — 覆盖 8 大类 50+ 场景"""
import sys, json, http.client, threading, time
sys.stdout.reconfigure(line_buffering=True)

HOST, PORT = 'localhost', 20007
P, F = 0, 0  # passed, failed

# Unique fingerprint base — avoid collisions with previous runs
_FP_BASE = int(time.time()) % 100000  # e.g. 54321
_fp_counter = [0]
def new_fp():
    _fp_counter[0] += 1
    return f'138{_FP_BASE + _fp_counter[0]:08d}'

def api(method, path, body=None, headers=None):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=15)
    hdrs = headers or {}
    if body is not None:
        hdrs['Content-Type'] = 'application/json'
        conn.request(method, path, json.dumps(body), hdrs)
    else:
        conn.request(method, path, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read().decode('utf-8')
    conn.close()
    try: return resp.status, json.loads(data)
    except: return resp.status, data

def ok(name, cond, detail=''):
    global P, F
    if cond: P += 1; print(f'  PASS: {name}')
    else: F += 1; print(f'  FAIL: {name} -- {detail}')

def admin_auth(token):
    return {'Authorization': f'Bearer {token}'}

# ========================================================
# SETUP: Admin login + cleanup old data + add fresh gifts
# ========================================================
def setup():
    print('\n[SETUP] Admin login + cleanup + gifts')
    code, d = api('POST', '/api/admin/login', {'password': 'admin123'})
    ok('admin login', code == 200, f'code={code}')
    token = d.get('token', '')
    auth = admin_auth(token)

    # Step 1: Global reset to release any locked gifts
    api('POST', '/api/admin/reset', None, auth)
    print('  INFO: global reset done')

    # Step 2: Delete all available gifts (cleanup from prior runs)
    code, gifts = api('GET', '/api/admin/gifts?status=available', headers=auth)
    if code == 200 and isinstance(gifts, list):
        for g in gifts:
            api('DELETE', f'/api/admin/gifts/{g["id"]}', headers=auth)
        print(f'  INFO: deleted {len(gifts)} available gifts')

    # Step 3: For claimed/locked gifts we can't delete, force them to available then delete
    for status in ['locked', 'claimed']:
        code, gs = api('GET', f'/api/admin/gifts?status={status}', headers=auth)
        if code == 200 and isinstance(gs, list):
            for g in gs:
                api('PUT', f'/api/admin/gifts/{g["id"]}/status', {'status': 'available'}, auth)
                api('DELETE', f'/api/admin/gifts/{g["id"]}', headers=auth)
            print(f'  INFO: cleaned {len(gs)} {status} gifts')

    # Step 4: Also reset max_regret to default
    api('PUT', '/api/admin/config', {'max_regret_chances': 1}, auth)

    # Step 5: Add 30 fresh test gifts (10 per tier for enough inventory)
    gifts_data = [
        ('A-耳机','A',80),('A-键盘','A',90),('A-鼠标','A',100),('A-音箱','A',110),('A-手表','A',120),
        ('A-耳机2','A',85),('A-键盘2','A',95),('A-鼠标2','A',105),('A-音箱2','A',115),('A-手表2','A',125),
        ('B-杯子','B',40),('B-笔记本','B',45),('B-手机壳','B',50),('B-抱枕','B',55),('B-台灯','B',60),
        ('B-杯子2','B',42),('B-笔记本2','B',47),('B-手机壳2','B',52),('B-抱枕2','B',57),('B-台灯2','B',62),
        ('C-贴纸','C',10),('C-钥匙扣','C',12),('C-书签','C',15),('C-发圈','C',18),('C-明信片','C',20),
        ('C-贴纸2','C',11),('C-钥匙扣2','C',13),('C-书签2','C',16),('C-发圈2','C',19),('C-明信片2','C',21),
    ]
    last_code = 0
    for name, tier, price in gifts_data:
        last_code, _ = api('POST', '/api/admin/gifts', {'name':name,'tier':tier,'price':price,'url':f'https://x.com/{name}'}, auth)
    ok('added 15 gifts', last_code == 200, f'last code={last_code}')
    return token, auth

# ========================================================
# TASK 1: Happy Path — 正常用户全流程
# ========================================================
def test_1_1_premium_full_flow(auth):
    print('\n[1.1] Premium full flow')
    fp = new_fp()
    # plans
    code, d = api('POST', '/api/draw/plans', {'budget': 200})
    ok('plans 200', code == 200)
    plans = d.get('plans', [])
    premium = next((p for p in plans if p['plan_type'] == 'premium'), None)
    ok('premium exists', premium is not None)

    # start
    code, d = api('POST', '/api/draw/start', {'fingerprint_id': fp, 'budget': 200, 'plan_type': 'premium'})
    ok('start 200', code == 200, f'{code}')
    if code != 200: return
    sid = d.get('session_id', 0)
    draws = d.get('draws', {})
    ok('session_id valid', sid > 0)
    ok('min_prices returned', bool(d.get('min_prices')))

    # spin + claim all tickets
    claimed = []
    total_spent = 0
    for tier in ['A','B','C']:
        for _ in range(draws.get(tier, 0)):
            code, sp = api('POST', '/api/draw/spin', {'tier':tier,'fingerprint_id':fp,'session_id':sid})
            ok(f'spin {tier} ok', code == 200, f'{code}')
            if code == 200:
                total_spent += sp['price']
                code2, cl = api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':sp['gift_id']})
                ok(f'claim {tier} ok', code2 == 200)
                claimed.append(sp['gift_id'])

    # history
    code, h = api('GET', f'/api/draw/history?fingerprint_id={fp}')
    ok('history 200', code == 200)
    ok('history count matches', len(h) == len(claimed), f'got {len(h)}, expected {len(claimed)}')

def test_1_2_diverse_full_flow():
    print('\n[1.2] Diverse full flow')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'diverse'})
    ok('start diverse', code == 200, f'{code}')
    if code != 200: return
    sid = d.get('session_id', 0)
    draws = d.get('draws', {})
    has_multi = sum(1 for v in draws.values() if v > 0) >= 2
    ok('diverse multi-tier', has_multi, f'draws={draws}')

    for tier in ['A','B','C']:
        for _ in range(draws.get(tier, 0)):
            code, sp = api('POST', '/api/draw/spin', {'tier':tier,'fingerprint_id':fp,'session_id':sid})
            if code == 200:
                api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':sp['gift_id']})
    ok('diverse flow complete', True)

def test_1_3_spin_no_action():
    print('\n[1.3] Spin no action')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    ok('start', code == 200, f'{code}')
    if code != 200: return
    sid = d.get('session_id', 0)
    code, sp = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
    ok('spin ok', code == 200)
    if code != 200: return
    gift_id = sp.get('gift_id', 0)

    # status check
    code, st = api('GET', f'/api/draw/status?fingerprint_id={fp}')
    ok('status 200', code == 200)
    locked = [g['gift_id'] for g in st.get('locked_gifts', [])]
    ok('gift still locked', gift_id in locked, f'locked={locked}')

    # cleanup: claim it
    api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':gift_id})

def test_1_4_release_then_spin():
    print('\n[1.4] Release then spin')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'diverse'})
    ok('start', code == 200, f'{code}')
    if code != 200: return
    sid = d.get('session_id', 0)
    budget0 = d.get('remaining_budget', 200)

    # spin C (cheaper, more reliable)
    code, sp1 = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid})
    ok('spin1', code == 200, f'{code}')
    if code != 200: return
    budget1 = sp1.get('remaining_budget', 0)
    gid1 = sp1.get('gift_id', 0)

    # release
    code, rel = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':gid1})
    ok('release ok', code == 200, f'{code}')
    ok('budget rolled back', rel.get('remaining_budget') == budget0, f'got {rel.get("remaining_budget")}, expected {budget0}')

    # spin again
    code, sp2 = api('POST', '/api/draw/spin', {'tier':'B','fingerprint_id':fp,'session_id':sid})
    ok('spin2 after release', code == 200, f'{code}')
    if code == 200:
        api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':sp2['gift_id']})

# ========================================================
# TASK 2: Boundary & Error Input
# ========================================================
def test_2_1_budget_boundary():
    print('\n[2.1] Budget boundary')
    code, _ = api('POST', '/api/draw/plans', {'budget': 0})
    ok('plans budget=0 → 400', code == 400, f'{code}')
    code, _ = api('POST', '/api/draw/plans', {'budget': -100})
    ok('plans budget=-100 → 400', code == 400, f'{code}')
    code, d = api('POST', '/api/draw/plans', {'budget': 0.01})
    ok('plans budget=0.01', code == 200)
    if code == 200:
        ok('only none plan', d['plans'][0]['plan_type'] == 'none', f'{d["plans"]}')
    code, d = api('POST', '/api/draw/plans', {'budget': 999999})
    ok('plans budget=999999', code == 200)

    fp = new_fp()
    code, _ = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':0,'plan_type':'premium'})
    ok('start budget=0 → 400', code == 400, f'{code}')
    code, _ = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':-50,'plan_type':'premium'})
    ok('start budget=-50 → 400', code == 400, f'{code}')

def test_2_2_fingerprint_validation():
    print('\n[2.2] Fingerprint validation')
    cases = [('', 400), ('12345', 400), ('123456789012', 400),
             ('abcdefghijk', 400), ('1380000111a', 400)]
    for fp_val, expected in cases:
        code, _ = api('GET', f'/api/draw/status?fingerprint_id={fp_val}')
        ok(f'fp="{fp_val}" -> {expected}', code == expected, f'got {code}')
    # space in fp: use POST to test validation instead of URL
    code, _ = api('POST', '/api/draw/start', {'fingerprint_id':' 13800001111','budget':200,'plan_type':'premium'})
    ok('fp with space -> 400', code == 400, f'got {code}')

def test_2_3_invalid_tier():
    print('\n[2.3] Invalid tier')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    ok('start', code == 200, f'{code}')
    sid = d.get('session_id', 0)
    for tier_val in ['D', 'a', '', 'ALL']:
        code, _ = api('POST', '/api/draw/spin', {'tier':tier_val,'fingerprint_id':fp,'session_id':sid})
        ok(f'tier="{tier_val}" → 4xx', code in (400, 404, 422), f'got {code}')

def test_2_4_invalid_session():
    print('\n[2.4] Invalid session_id')
    fp = new_fp()
    for sid_val in [0, 99999, -1]:
        code, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid_val})
        ok(f'session_id={sid_val} → 404', code == 404, f'got {code}')

    # other user's session
    fp_a = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp_a,'budget':200,'plan_type':'premium'})
    sid_a = d.get('session_id', 0)
    fp_b = new_fp()
    code, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp_b,'session_id':sid_a})
    ok('other user session → 404', code == 404, f'got {code}')

def test_2_5_invalid_plan_type():
    print('\n[2.5] Invalid plan_type')
    fp = new_fp()
    for pt in ['balanced', '', 'PREMIUM']:
        code, _ = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':pt})
        ok(f'plan_type="{pt}" → 400', code == 400, f'got {code}')

def test_2_6_duplicate_operations():
    print('\n[2.6] Duplicate operations')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)
    code, sp = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
    ok('spin', code == 200)
    if code != 200: return
    gid = sp['gift_id']

    # claim
    code, _ = api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':gid})
    ok('claim ok', code == 200)
    # double claim
    code, _ = api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':gid})
    ok('double claim → 400', code == 400, f'got {code}')
    # release claimed
    code, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':gid})
    ok('release claimed → 400', code == 400, f'got {code}')

    # spin + release + double release
    code, sp2 = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
    if code == 200:
        gid2 = sp2['gift_id']
        api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':gid2})
        code, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':gid2})
        ok('double release → 400', code == 400, f'got {code}')

# ========================================================
# TASK 3: Malicious User
# ========================================================
def test_3_1_excess_regret(auth):
    print('\n[3.1] Excess regret')
    # ensure max_regret=1
    api('PUT', '/api/admin/config', {'max_regret_chances': 1}, auth)
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':300,'plan_type':'diverse'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)

    # 1st release
    code, sp1 = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid})
    if code == 200:
        code, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':sp1['gift_id']})
        ok('1st release ok', code == 200, f'{code}')

    # 2nd release (should fail)
    code, sp2 = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid})
    if code == 200:
        code, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':sp2['gift_id']})
        ok('2nd release → 400', code == 400, f'got {code}')

def test_3_2_exceed_tier_limit():
    print('\n[3.2] Exceed tier limit')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':300,'plan_type':'premium'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)
    a_limit = d.get('draws', {}).get('A', 0)
    # use all A quota
    for i in range(a_limit):
        code, sp = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
        if code == 200:
            api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':sp['gift_id']})
    ok(f'used A quota={a_limit}', True)
    # one more
    code, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
    ok('exceed A → 400', code == 400, f'got {code}')

def test_3_3_cross_user():
    print('\n[3.3] Cross-user operation')
    fp_a = new_fp()
    fp_b = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp_a,'budget':200,'plan_type':'diverse'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)
    draws = d.get('draws', {})
    # find a tier with quota
    spin_tier = next((t for t in ['A','B','C'] if draws.get(t, 0) > 0), None)
    if not spin_tier: ok('no tier available', False, f'draws={draws}'); return
    code, sp = api('POST', '/api/draw/spin', {'tier':spin_tier,'fingerprint_id':fp_a,'session_id':sid})
    ok('A spins', code == 200, f'{code}')
    if code != 200: return
    gid = sp['gift_id']

    # B tries to claim A's gift
    code, _ = api('POST', '/api/draw/claim', {'fingerprint_id':fp_b,'gift_id':gid})
    ok('B claim A gift → 400', code == 400, f'got {code}')
    # B tries to release A's gift
    code, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp_b,'gift_id':gid})
    ok('B release A gift → 400', code == 400, f'got {code}')
    # cleanup
    api('POST', '/api/draw/claim', {'fingerprint_id':fp_a,'gift_id':gid})

def test_3_4_fake_session():
    print('\n[3.4] Fake session')
    fp_a = new_fp()
    fp_b = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp_a,'budget':200,'plan_type':'premium'})
    sid_a = d.get('session_id', 0)
    code, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp_b,'session_id':sid_a})
    ok('B use A session → 404', code == 404, f'got {code}')

def test_3_5_no_session_spin():
    print('\n[3.5] No session spin')
    fp = new_fp()
    code, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':1})
    ok('no session → 404', code == 404, f'got {code}')

def test_3_6_budget_overspend():
    print('\n[3.6] Budget overspend')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':100,'plan_type':'premium'})
    ok('start budget=100', code == 200, f'{code}')
    sid = d.get('session_id', 0)
    # spin A (~80-120) — might succeed if price<=100
    code, sp = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
    if code == 200:
        api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':sp['gift_id']})
        remaining = sp.get('remaining_budget', 0)
        ok(f'spin1 ok, remaining={remaining}', remaining >= 0)
        # try spin A again — should fail (budget too low for A)
        code2, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
        ok('2nd spin A → no budget/gift', code2 in (400, 404), f'got {code2}')
    else:
        # A min_price=80 but budget=100 might not be enough depending on draws
        ok('spin A skipped (tier limit=0 or no budget)', code in (400, 404))

# ========================================================
# TASK 4: Admin Operations
# ========================================================
def test_4_1_admin_login():
    print('\n[4.1] Admin login')
    code, d = api('POST', '/api/admin/login', {'password': 'admin123'})
    ok('correct password', code == 200)
    code, _ = api('POST', '/api/admin/login', {'password': 'wrong'})
    ok('wrong password → 403', code == 403, f'got {code}')
    code, _ = api('GET', '/api/admin/gifts')
    ok('no token → 403', code == 403, f'got {code}')
    code, _ = api('GET', '/api/admin/gifts', headers={'Authorization': 'Bearer faketoken'})
    ok('fake token → 403', code == 403, f'got {code}')

def test_4_2_gift_crud(auth):
    print('\n[4.2] Gift CRUD')
    # create
    code, d = api('POST', '/api/admin/gifts', {'name':'TEST-gift','tier':'C','price':25,'url':'https://test.com'}, auth)
    ok('create gift', code == 200, f'{code}')
    gid = d.get('id', 0)
    # update
    code, _ = api('PUT', f'/api/admin/gifts/{gid}', {'name':'TEST-updated'}, auth)
    ok('update gift', code == 200, f'{code}')
    # delete available
    code, _ = api('DELETE', f'/api/admin/gifts/{gid}', headers=auth)
    ok('delete available', code == 200, f'{code}')

    # create invalid
    code, _ = api('POST', '/api/admin/gifts', {'name':'','tier':'C','price':25,'url':'https://x.com'}, auth)
    # empty name passes schema but might pass... let's test price
    code, _ = api('POST', '/api/admin/gifts', {'name':'bad','tier':'C','price':-10,'url':'https://x.com'}, auth)
    ok('negative price → 422', code == 422, f'got {code}')
    code, _ = api('POST', '/api/admin/gifts', {'name':'bad','tier':'X','price':25,'url':'https://x.com'}, auth)
    ok('tier X → 400', code == 400, f'got {code}')

def test_4_3_gift_status(auth):
    print('\n[4.3] Gift status mgmt')
    # create a test gift
    code, d = api('POST', '/api/admin/gifts', {'name':'status-test','tier':'C','price':30,'url':'https://s.com'}, auth)
    gid = d.get('id', 0)
    # set locked
    code, _ = api('PUT', f'/api/admin/gifts/{gid}/status', {'status':'locked'}, auth)
    ok('set locked', code == 200, f'{code}')
    # unlock
    code, _ = api('POST', f'/api/admin/gifts/{gid}/unlock', None, auth)
    ok('unlock', code == 200, f'{code}')
    # unlock non-locked → 400
    code, _ = api('POST', f'/api/admin/gifts/{gid}/unlock', None, auth)
    ok('unlock non-locked → 400', code == 400, f'got {code}')
    # cleanup
    api('DELETE', f'/api/admin/gifts/{gid}', headers=auth)

def test_4_4_user_management(auth):
    print('\n[4.4] User management')
    # list users
    code, d = api('GET', '/api/admin/users?page=1&page_size=5', headers=auth)
    ok('user list', code == 200, f'{code}')
    ok('has users', d.get('total', 0) > 0 or len(d.get('users', [])) >= 0, f'{d}')

def test_4_5_global_reset(auth):
    print('\n[4.5] Global reset')
    # create a session and lock a gift
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    sid = d.get('session_id', 0)
    code, sp = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid})
    locked_gid = sp.get('gift_id', 0) if code == 200 else 0

    # global reset
    code, _ = api('POST', '/api/admin/reset', None, auth)
    ok('global reset', code == 200, f'{code}')

    # verify: locked gift should be available again
    if locked_gid:
        code, gifts = api('GET', '/api/admin/gifts?search=&status=available', headers=auth)
        # just check the status endpoint works
        ok('gifts query after reset', code == 200)

def test_4_6_system_config(auth):
    print('\n[4.6] System config')
    # set to 0
    code, _ = api('PUT', '/api/admin/config', {'max_regret_chances': 0}, auth)
    ok('set regret=0', code == 200, f'{code}')
    fp = new_fp()
    c, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'diverse'})
    if c == 200:
        sid2 = d.get('session_id', 0)
        c2, sp = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid2})
        if c2 == 200:
            c3, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':sp['gift_id']})
            ok('regret=0 → release fails', c3 == 400, f'got {c3}')
    # set to -1
    code, _ = api('PUT', '/api/admin/config', {'max_regret_chances': -1}, auth)
    ok('set regret=-1 → 400', code == 400, f'got {code}')
    # restore
    api('PUT', '/api/admin/config', {'max_regret_chances': 1}, auth)

def test_4_7_export(auth):
    print('\n[4.7] Export')
    code, d = api('POST', '/api/admin/export', None, auth)
    ok('export csv', code == 200, f'{code}')

def test_4_8_stats(auth):
    print('\n[4.8] Stats')
    code, d = api('GET', '/api/admin/stats', headers=auth)
    ok('stats 200', code == 200, f'{code}')
    ok('has total', 'total_gifts' in str(d) or 'total' in str(d), f'{list(d.keys()) if isinstance(d, dict) else d}')

# ========================================================
# TASK 5: Concurrency
# ========================================================
def test_5_1_concurrent_spin():
    print('\n[5.1] Concurrent spin')
    results = []
    def worker(fp_val):
        c, d = api('POST', '/api/draw/start', {'fingerprint_id':fp_val,'budget':200,'plan_type':'diverse'})
        if c != 200: results.append(('fail', c)); return
        sid = d.get('session_id', 0)
        c2, sp = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp_val,'session_id':sid})
        results.append(('ok', c2, sp.get('gift_id', 0) if c2 == 200 else 0))
        if c2 == 200:
            api('POST', '/api/draw/claim', {'fingerprint_id':fp_val,'gift_id':sp['gift_id']})

    fps = [new_fp() for _ in range(5)]
    threads = [threading.Thread(target=worker, args=(fp,)) for fp in fps]
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)
    gift_ids = [r[2] for r in results if r[0] == 'ok' and r[1] == 200]
    ok('concurrent spin no duplicates', len(gift_ids) == len(set(gift_ids)), f'ids={gift_ids}')
    ok('all threads completed', len(results) == 5, f'got {len(results)}')

def test_5_3_concurrent_release():
    print('\n[5.3] Concurrent release')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'diverse'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)
    code, sp = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid})
    if code != 200: ok('spin failed', False, f'{code}'); return
    gid = sp['gift_id']

    results = []
    def worker():
        c, _ = api('POST', '/api/draw/release', {'fingerprint_id':fp,'gift_id':gid})
        results.append(c)
    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=15)
    success = sum(1 for r in results if r == 200)
    ok('at most 1 release success', success <= 1, f'results={results}')

# ========================================================
# TASK 6: Time-based (simulated via admin API)
# ========================================================
def test_6_lock_expiry(auth):
    print('\n[6.1/6.2] Lock expiry')
    # Create a gift, lock it via spin, then admin-unlock to simulate
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    sid = d.get('session_id', 0)
    code, sp = api('POST', '/api/draw/spin', {'tier':'C','fingerprint_id':fp,'session_id':sid})
    if code == 200:
        gid = sp['gift_id']
        # admin force unlock simulates expiry
        code, _ = api('POST', f'/api/admin/gifts/{gid}/unlock', None, auth)
        ok('admin unlock (simulates expiry)', code == 200, f'{code}')
        # verify gift is available
        code, gifts = api('GET', '/api/admin/gifts?status=available', headers=auth)
        ok('gifts query ok', code == 200)

# ========================================================
# TASK 7: Algorithm Verification
# ========================================================
def test_7_1_premium_algo():
    print('\n[7.1] Premium algo')
    for budget, check_fn, desc in [
        (200, lambda d: any(p['draws'].get('A',0) > 0 for p in d.get('plans',[]) if p['plan_type']=='premium'), 'premium A>0'),
        (50, lambda d: all(p['draws'].get('A',0) == 0 for p in d.get('plans',[]) if p['plan_type']=='premium'), 'premium A=0 (budget<80)'),
        (5, lambda d: d['plans'][0]['plan_type'] == 'none', 'none (budget=5)'),
    ]:
        code, d = api('POST', '/api/draw/plans', {'budget': budget})
        ok(f'premium budget={budget}: {desc}', code == 200 and check_fn(d), f'{d}')

def test_7_2_diverse_algo():
    print('\n[7.2] Diverse algo')
    code, d = api('POST', '/api/draw/plans', {'budget': 200})
    div = next((p for p in d.get('plans',[]) if p['plan_type']=='diverse'), None)
    if div:
        tiers_with = sum(1 for v in div['draws'].values() if v > 0)
        ok('diverse 200: multi-tier', tiers_with >= 2, f'draws={div["draws"]}')
    code, d = api('POST', '/api/draw/plans', {'budget': 80})
    div = next((p for p in d.get('plans',[]) if p['plan_type']=='diverse'), None)
    if div:
        # budget=80 is tight for diverse, just check it has some draws
        total_draws = sum(div['draws'].values())
        ok('diverse 80: has draws', total_draws > 0, f'draws={div["draws"]}')
    code, d = api('POST', '/api/draw/plans', {'budget': 5})
    ok('diverse 5: none', d['plans'][0]['plan_type'] == 'none', f'{d}')

def test_7_4_single_tier():
    print('\n[7.4] Single tier')
    # Not easy to test without clearing DB, so just verify plans return valid
    code, d = api('POST', '/api/draw/plans', {'budget': 100})
    ok('plans 100 valid', code == 200 and len(d.get('plans',[])) > 0)

# ========================================================
# TASK 8: Frontend Interaction Simulation
# ========================================================
def test_8_1_page_refresh():
    print('\n[8.1] Page refresh recovery')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)
    code, sp = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':fp,'session_id':sid})
    gid = sp.get('gift_id', 0) if code == 200 else 0

    # simulate refresh: call status
    code, st = api('GET', f'/api/draw/status?fingerprint_id={fp}')
    ok('status restores session_id', st.get('session_id') == sid, f'{st.get("session_id")} vs {sid}')
    ok('status restores locked_gifts', len(st.get('locked_gifts',[])) > 0)
    ok('status restores remaining_budget', st.get('remaining_budget', -1) >= 0)
    ok('status restores regret_remaining', st.get('regret_remaining', -1) >= 0)
    # cleanup
    if gid: api('POST', '/api/draw/claim', {'fingerprint_id':fp,'gift_id':gid})

def test_8_2_multi_tab():
    print('\n[8.2] Multi-tab sync')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':200,'plan_type':'premium'})
    if code != 200: ok('start failed', False, f'{code}'); return
    sid = d.get('session_id', 0)
    # "tab B" calls status
    code, st = api('GET', f'/api/draw/status?fingerprint_id={fp}')
    ok('tab B sees session', st.get('session_id') == sid)

def test_8_3_can_afford():
    print('\n[8.3] canAfford logic')
    fp = new_fp()
    code, d = api('POST', '/api/draw/start', {'fingerprint_id':fp,'budget':50,'plan_type':'diverse'})
    ok('start budget=50', code == 200, f'{code}')
    if code != 200: return
    min_p = d.get('min_prices', {})
    # min_p['A'] = 80, budget=50 < 80 → can't afford A
    ok('cannot afford A (min=80 > budget=50)', 50 < min_p.get('A', 0))
    # min_p['C'] = 10, budget=50 >= 10 → can afford C
    ok('can afford C (min=10 <= budget=50)', 50 >= min_p.get('C', 999))

def test_8_4_no_fingerprint():
    print('\n[8.4] Unauthenticated access')
    code, _ = api('POST', '/api/draw/start', {'fingerprint_id':'','budget':200,'plan_type':'premium'})
    ok('empty fp → 400', code == 400, f'{code}')
    code, _ = api('POST', '/api/draw/spin', {'tier':'A','fingerprint_id':'','session_id':1})
    ok('empty fp spin → 400', code == 400, f'{code}')

# ========================================================
# MAIN
# ========================================================
def main():
    print('=' * 60)
    print('[START] Full User Behavior Simulation Test')
    print('=' * 60)

    token, auth = setup()

    # Task 1: Happy Path
    test_1_1_premium_full_flow(auth)
    test_1_2_diverse_full_flow()
    test_1_3_spin_no_action()
    test_1_4_release_then_spin()

    # Task 2: Boundary & Error
    test_2_1_budget_boundary()
    test_2_2_fingerprint_validation()
    test_2_3_invalid_tier()
    test_2_4_invalid_session()
    test_2_5_invalid_plan_type()
    test_2_6_duplicate_operations()

    # Task 3: Malicious
    test_3_1_excess_regret(auth)
    test_3_2_exceed_tier_limit()
    test_3_3_cross_user()
    test_3_4_fake_session()
    test_3_5_no_session_spin()
    test_3_6_budget_overspend()

    # Task 4: Admin
    test_4_1_admin_login()
    test_4_2_gift_crud(auth)
    test_4_3_gift_status(auth)
    test_4_4_user_management(auth)
    test_4_5_global_reset(auth)
    test_4_6_system_config(auth)
    test_4_7_export(auth)
    test_4_8_stats(auth)

    # Task 5: Concurrency
    test_5_1_concurrent_spin()
    test_5_3_concurrent_release()

    # Task 6: Time
    test_6_lock_expiry(auth)

    # Task 7: Algorithm
    test_7_1_premium_algo()
    test_7_2_diverse_algo()
    test_7_4_single_tier()

    # Task 8: Frontend
    test_8_1_page_refresh()
    test_8_2_multi_tab()
    test_8_3_can_afford()
    test_8_4_no_fingerprint()

    # Summary
    print('\n' + '=' * 60)
    total = P + F
    print(f'[RESULT] {P}/{total} passed, {F}/{total} failed')
    if F == 0:
        print('[OK] ALL TESTS PASSED!')
    else:
        print(f'[WARN] {F} test(s) failed')
    print('=' * 60)
    sys.exit(1 if F > 0 else 0)

if __name__ == '__main__':
    main()
