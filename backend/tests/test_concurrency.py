"""
Concurrency stress test - simplified version
"""
import http.client
import json
import threading
import time
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

BASE_HOST = "127.0.0.1"
BASE_PORT = 20001
ADMIN_PASSWORD = "admin123"

passed = 0
failed = 0

def log(msg):
    print(msg, flush=True)

def http_req(method, path, data=None, headers=None):
    conn = http.client.HTTPConnection(BASE_HOST, BASE_PORT, timeout=15)
    body = json.dumps(data) if data else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    try:
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read().decode('utf-8')
        try:
            jdata = json.loads(raw)
        except Exception:
            jdata = raw
        conn.close()
        return resp.status, jdata
    except Exception as e:
        try: conn.close()
        except: pass
        return 0, str(e)

def admin_login():
    code, data = http_req("POST", "/api/admin/login", {"password": ADMIN_PASSWORD})
    if code == 200:
        return data["token"]
    log(f"[FAIL] Admin login: {code} {data}")
    return None

def setup_gifts(token):
    h = {"Authorization": f"Bearer {token}"}
    # Reset first
    http_req("POST", "/api/admin/reset", headers=h)
    # Add 30 gifts (10 per tier)
    for tier, pr in [('A', (80, 120)), ('B', (30, 60)), ('C', (5, 20))]:
        for i in range(10):
            price = pr[0] + (pr[1] - pr[0]) * i // 10
            http_req("POST", "/api/admin/gifts", {
                "name": f"{tier}-gift-{i+1}", "tier": tier,
                "price": price, "url": f"https://ex.com/{tier}/{i}",
                "weight": 10,
            }, h)
    log("[OK] Setup: 30 gifts created")

def start_session(phone, budget=200, plan_type="diverse"):
    code, data = http_req("POST", "/api/draw/start", {
        "fingerprint_id": phone, "budget": budget, "plan_type": plan_type,
    })
    if code == 200:
        return data
    log(f"  [WARN] start_session({phone}): {code} {json.dumps(data, ensure_ascii=False)}")
    return None

# ========= TC1: 5 users concurrent spin =========
def test_tc1():
    global passed, failed
    log("\n--- TC1: 5 users concurrent spin (tier C) ---")
    phones = [f"1380000{i:04d}" for i in range(1, 6)]
    
    sessions = {}
    for p in phones:
        s = start_session(p, budget=200)
        if s:
            sessions[p] = s["session_id"]
    
    if len(sessions) < 5:
        log(f"  [SKIP] Only {len(sessions)} sessions created")
        return
    
    results = {}
    barrier = threading.Barrier(5)
    
    def spin(phone):
        barrier.wait(timeout=10)
        code, data = http_req("POST", "/api/draw/spin", {
            "fingerprint_id": phone,
            "session_id": sessions[phone],
            "tier": "C",
        })
        results[phone] = (code, data)
    
    threads = [threading.Thread(target=spin, args=(p,)) for p in phones]
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)
    
    gift_ids = []
    ok_count = 0
    for p, (code, data) in results.items():
        if code == 200:
            ok_count += 1
            gift_ids.append(data.get("gift_id"))
    
    unique = len(set(gift_ids))
    if unique == len(gift_ids) and ok_count == 5:
        log(f"  [PASS] {ok_count} spins OK, {unique} unique gifts locked")
        passed += 1
    else:
        log(f"  [FAIL] {ok_count} OK, gift_ids={gift_ids}, unique={unique}")
        failed += 1

# ========= TC2: spin then claim =========
def test_tc2():
    global passed, failed
    log("\n--- TC2: spin then claim ---")
    phone = "13800001001"
    s = start_session(phone, budget=200)
    if not s:
        log("  [SKIP] No session"); return
    
    code, data = http_req("POST", "/api/draw/spin", {
        "fingerprint_id": phone, "session_id": s["session_id"], "tier": "B",
    })
    if code != 200:
        log(f"  [FAIL] Spin: {code}"); failed += 1; return
    
    gid = data.get("gift_id")
    code, data = http_req("POST", "/api/draw/claim", {
        "fingerprint_id": phone, "gift_id": gid,
    })
    if code == 200:
        log(f"  [PASS] Claim OK for gift#{gid}")
        passed += 1
    else:
        log(f"  [FAIL] Claim: {code} {data}")
        failed += 1

# ========= TC3: regret race =========
def test_tc3():
    global passed, failed
    log("\n--- TC3: regret race condition ---")
    phone = "13800002001"
    token = admin_login()
    h = {"Authorization": f"Bearer {token}"}
    http_req("PUT", "/api/admin/config", {"max_regret_chances": 1}, h)
    
    s = start_session(phone, budget=300)
    if not s:
        log("  [SKIP] No session"); return
    
    gift_ids = []
    for tier in ["B", "C"]:
        code, data = http_req("POST", "/api/draw/spin", {
            "fingerprint_id": phone, "session_id": s["session_id"], "tier": tier,
        })
        if code == 200:
            gift_ids.append(data.get("gift_id"))
    
    if len(gift_ids) < 2:
        log(f"  [SKIP] Only {len(gift_ids)} gifts spun"); return
    
    log(f"  Locked: {gift_ids}")
    release_results = {}
    barrier = threading.Barrier(2)
    
    def try_release(gid):
        barrier.wait(timeout=10)
        code, data = http_req("POST", "/api/draw/release", {
            "fingerprint_id": phone, "gift_id": gid,
        })
        release_results[gid] = code
    
    threads = [threading.Thread(target=try_release, args=(gid,)) for gid in gift_ids]
    for t in threads: t.start()
    for t in threads: t.join(timeout=15)
    
    ok_count = sum(1 for c in release_results.values() if c == 200)
    if ok_count <= 1:
        log(f"  [PASS] {ok_count} release(s) OK (max=1)")
        passed += 1
    else:
        log(f"  [FAIL] {ok_count} releases OK, expected <= 1")
        failed += 1
    
    # Restore config
    http_req("PUT", "/api/admin/config", {"max_regret_chances": 3}, h)

# ========= TC4: admin reset during draw =========
def test_tc4():
    global passed, failed
    log("\n--- TC4: admin reset during user draw ---")
    token = admin_login()
    h = {"Authorization": f"Bearer {token}"}
    phone = "13800003001"
    
    s = start_session(phone, budget=200)
    if not s:
        log("  [SKIP] No session"); return
    
    code, data = http_req("POST", "/api/draw/spin", {
        "fingerprint_id": phone, "session_id": s["session_id"], "tier": "C",
    })
    if code != 200:
        log(f"  [SKIP] Spin: {code}"); return
    
    gid = data.get("gift_id")
    barrier = threading.Barrier(2)
    claim_code = [0]
    reset_code = [0]
    
    def user_claim():
        barrier.wait(timeout=10)
        c, _ = http_req("POST", "/api/draw/claim", {
            "fingerprint_id": phone, "gift_id": gid,
        })
        claim_code[0] = c
    
    def admin_reset():
        barrier.wait(timeout=10)
        c, _ = http_req("POST", "/api/admin/reset", headers=h)
        reset_code[0] = c
    
    t1 = threading.Thread(target=user_claim)
    t2 = threading.Thread(target=admin_reset)
    t1.start(); t2.start()
    t1.join(timeout=15); t2.join(timeout=15)
    
    log(f"  claim={claim_code[0]}, reset={reset_code[0]}")
    if claim_code[0] > 0 and reset_code[0] > 0:
        log(f"  [PASS] No crash")
        passed += 1
    else:
        log(f"  [FAIL] Incomplete")
        failed += 1

# ========= TC5: data consistency =========
def test_tc5():
    global passed, failed
    log("\n--- TC5: data consistency audit ---")
    token = admin_login()
    h = {"Authorization": f"Bearer {token}"}
    
    code, gifts = http_req("GET", "/api/admin/gifts", headers=h)
    if code != 200:
        log(f"  [FAIL] GET gifts: {code}"); failed += 1; return
    
    claimed = [g for g in gifts if g.get("status") == "claimed"]
    locked = [g for g in gifts if g.get("status") == "locked"]
    avail = [g for g in gifts if g.get("status") == "available"]
    
    log(f"  Total={len(gifts)}, Avail={len(avail)}, Locked={len(locked)}, Claimed={len(claimed)}")
    
    # claimed should have claimed_by
    bad = [g for g in claimed if not g.get("claimed_by")]
    if bad:
        log(f"  [FAIL] {len(bad)} claimed without claimed_by"); failed += 1
    else:
        log(f"  [PASS] All claimed have claimed_by"); passed += 1
    
    # locked should have locked_by
    bad = [g for g in locked if not g.get("locked_by")]
    if bad:
        log(f"  [FAIL] {len(bad)} locked without locked_by"); failed += 1
    else:
        log(f"  [PASS] All locked have locked_by"); passed += 1
    
    # no overlap
    claimed_ids = {g["id"] for g in claimed}
    locked_ids = {g["id"] for g in locked}
    if claimed_ids & locked_ids:
        log(f"  [FAIL] Overlap: {claimed_ids & locked_ids}"); failed += 1
    else:
        log(f"  [PASS] No overlap"); passed += 1

# ========= Main =========
def main():
    log("=" * 50)
    log("  Birthday Gift Concurrency Stress Test")
    log("=" * 50)
    
    token = admin_login()
    if not token:
        log("[FATAL] Cannot login"); sys.exit(1)
    log("[OK] Admin logged in")
    
    setup_gifts(token)
    
    test_tc1()
    test_tc2()
    test_tc3()
    test_tc4()
    
    # Re-setup for consistency check
    setup_gifts(admin_login())
    test_tc5()
    
    log(f"\n{'='*50}")
    log(f"  Results: {passed} passed, {failed} failed")
    log(f"{'='*50}")

if __name__ == "__main__":
    main()
