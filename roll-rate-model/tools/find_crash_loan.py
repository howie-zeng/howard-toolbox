"""Binary search for the C++ crashing loan in upst_2026_2."""
import json, subprocess, sys, os

deal_dir = "input/deals/upst_2026_2"
json_path = os.path.join(deal_dir, "loans_prepped.json")

loans = json.load(open(json_path))
backup = list(loans)
print(f"Loaded {len(loans)} loans")

def test(n):
    json.dump(loans[:n], open(json_path, 'w'))
    r = subprocess.run(
        [r'.\build\Release\sim_main.exe', '--config', 'config/default.json',
         '--dup', '1', '--workers', '1', '--scen', 'debug'],
        capture_output=True, text=True, timeout=120)
    return 'Done in' in r.stdout

try:
    lo, hi = 1, len(loans)
    print(f"Testing 1...", end=" ", flush=True)
    if not test(1):
        print("CRASH at loan 0!")
        sys.exit(1)
    print("OK")

    print(f"Testing {hi}...", end=" ", flush=True)
    if test(hi):
        print("OK - no crash!")
        sys.exit(0)
    print("CRASH")

    while hi - lo > 1:
        mid = (lo + hi) // 2
        print(f"Testing {mid}...", end=" ", flush=True)
        if test(mid):
            print("OK")
            lo = mid
        else:
            print("CRASH")
            hi = mid

    bad = loans[hi - 1]
    print(f"\nCrash at loan index {hi-1}, loan_id={bad.get('loan_id')}")
    print(f"Dumping bad loan to {deal_dir}/bad_loan.json")
    json.dump(bad, open(os.path.join(deal_dir, "bad_loan.json"), 'w'), indent=2)
finally:
    json.dump(backup, open(json_path, 'w'))
    print("Restored original file")
