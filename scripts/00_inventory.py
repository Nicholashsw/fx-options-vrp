#!/usr/bin/env python3
"""Step 0: inventory of raw Databento job folders. No assumptions: roles are
derived from each job's metadata.json (schema + symbols)."""
import json, os, re, csv
from collections import defaultdict

BASE = os.environ.get("DATABENTO_BASE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
WORK = os.environ.get("FX_VRP_WORK", os.path.join(BASE, "fx_vrp_work"))
DIAG = os.path.join(WORK, "diagnostics")
os.makedirs(DIAG, exist_ok=True)

NEW_ROOTS = {"ADU.OPT", "GBU.OPT", "CAU.OPT", "EUU.OPT", "JPU.OPT", "CHU.OPT"}

def role_of(q):
    syms = set(q["symbols"])
    if syms & NEW_ROOTS:
        grp = "opt_new"
    elif all(s.endswith(".OPT") for s in syms):
        grp = "opt_old"
    elif all(s.endswith(".FUT") for s in syms):
        grp = "fut"
    else:
        grp = "UNKNOWN"
    kind = {"definition": "defs", "statistics": "stats"}.get(q["schema"], q["schema"])
    return f"{grp}_{kind}"

def month_range(a, b):  # inclusive "YYYY-MM" strings
    y, m = int(a[:4]), int(a[5:7])
    y2, m2 = int(b[:4]), int(b[5:7])
    out = []
    while (y, m) <= (y2, m2):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13: y, m = y + 1, 1
    return out

rows, summary = [], {}
for d in sorted(os.listdir(BASE)):
    p = os.path.join(BASE, d)
    if not (os.path.isdir(p) and d.startswith("GLBX-")):
        continue
    meta = json.load(open(os.path.join(p, "metadata.json")))
    q = meta.get("query", meta)
    role = role_of(q)
    start_ns, end_ns = int(q["start"]), int(q["end"])
    start = f"{start_ns // 10**9}"
    import datetime as dt
    sdate = dt.datetime.utcfromtimestamp(start_ns / 1e9).date()
    edate = dt.datetime.utcfromtimestamp(end_ns / 1e9).date()
    months_found, sizes = [], []
    for f in sorted(os.listdir(p)):
        if not f.endswith(".dbn.zst"):
            continue
        m = re.match(r"glbx-mdp3-(\d{8})-(\d{8})\.(\w+)\.dbn\.zst$", f)
        assert m, f"unparseable filename: {f}"
        d1, d2, schema_in_name = m.groups()
        assert schema_in_name == q["schema"], f"schema mismatch {f} vs {q['schema']}"
        month = f"{d1[:4]}-{d1[4:6]}"
        sz = os.path.getsize(os.path.join(p, f))
        months_found.append(month)
        sizes.append(sz)
        rows.append(dict(job=d, role=role, file=f, month=month, size_bytes=sz,
                         schema=q["schema"], symbols="|".join(sorted(q["symbols"]))))
    expected = month_range(str(sdate)[:7], str(edate)[:7])
    missing = sorted(set(expected) - set(months_found))
    dupmonths = sorted({m for m in months_found if months_found.count(m) > 1})
    summary[role] = dict(job=d, schema=q["schema"], n_symbols=len(q["symbols"]),
                         symbols=",".join(sorted(q["symbols"])),
                         start=str(sdate), end=str(edate),
                         n_files=len(months_found), n_expected=len(expected),
                         missing_months=";".join(missing) or "-",
                         dup_months=";".join(dupmonths) or "-",
                         total_mb=round(sum(sizes) / 2**20, 1),
                         max_file_mb=round(max(sizes) / 2**20, 1))

with open(os.path.join(DIAG, "inventory_files.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
with open(os.path.join(DIAG, "inventory_summary.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["role"] + list(next(iter(summary.values()))))
    w.writeheader()
    for r, v in sorted(summary.items()):
        w.writerow({"role": r, **v})

print(f"{'role':<15}{'files':>6}{'expect':>7}{'totMB':>9}{'maxMB':>7}  {'range':<24}missing")
for r, v in sorted(summary.items()):
    print(f"{r:<15}{v['n_files']:>6}{v['n_expected']:>7}{v['total_mb']:>9}{v['max_file_mb']:>7}  "
          f"{v['start']}..{v['end']}  {v['missing_months']}")
print(f"\ntotal files: {len(rows)}; any dup months: "
      f"{[ (r, v['dup_months']) for r, v in summary.items() if v['dup_months'] != '-' ] or 'none'}")
