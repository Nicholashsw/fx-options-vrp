#!/usr/bin/env python3
"""Step 1: DBN.ZST -> parquet. Converts on fast local disk, then copies to the
mounted output dir (virtiofs direct writes are ~12x slower). Resumable; call
repeatedly with a time budget until it prints ALL_DONE."""
import argparse, csv, os, shutil, tempfile, time
from multiprocessing import Pool

BASE = os.environ.get("DATABENTO_BASE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
WORK = os.environ.get("FX_VRP_WORK", os.path.join(BASE, "fx_vrp_work"))
INV = os.path.join(WORK, "diagnostics", "inventory_files.csv")
OUT = os.path.join(WORK, "parquet")
STAGE = os.environ.get("FX_VRP_STAGE", os.path.join(tempfile.gettempdir(), "fx_vrp_stage"))

def convert_one(task):
    src, stage_path, dst = task
    import databento as db
    try:
        db.DBNStore.from_file(src).to_parquet(
            stage_path, price_type="float", pretty_ts=True, map_symbols=False)
        return ("ok", stage_path, dst, "")
    except Exception as e:
        if os.path.exists(stage_path):
            os.remove(stage_path)
        return ("fail", stage_path, dst, f"{type(e).__name__}: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=30.0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(STAGE, exist_ok=True)
    for f in os.listdir(STAGE):  # leftovers from a previous interrupted call
        os.remove(os.path.join(STAGE, f))

    tasks = []
    with open(INV) as fh:
        for r in csv.DictReader(fh):
            dst = os.path.join(OUT, r["role"], r["month"] + ".parquet")
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            src = os.path.join(BASE, r["job"], r["file"])
            sp = os.path.join(STAGE, f"{r['role']}__{r['month']}.parquet")
            tasks.append((int(r["size_bytes"]), (src, sp, dst)))
    tasks.sort(key=lambda t: -t[0])
    if not tasks:
        print("ALL_DONE done=0 fail=0 remaining=0", flush=True)
        return
    queue = [t for _, t in tasks]

    done = failed = 0
    inflight = []
    pool = Pool(a.workers)
    MAXOUT = a.workers + 2
    while True:
        while queue and len(inflight) < MAXOUT and time.time() - t0 < a.budget:
            inflight.append(pool.apply_async(convert_one, (queue.pop(0),)))
        ready = [r for r in inflight if r.ready()]
        for r in ready:
            inflight.remove(r)
            status, sp, dst, err = r.get()
            if status == "ok":
                tmp = f"{dst}.tmp{os.getpid()}"
                shutil.copyfile(sp, tmp)   # copy staged file to mount
                os.replace(tmp, dst)
                os.remove(sp)
                done += 1
            else:
                failed += 1
                print("FAIL", dst, err, flush=True)
        over = time.time() - t0 > a.budget
        if over and not ready and inflight:
            # grace: wait briefly for in-flight conversions, then bail
            if time.time() - t0 > a.budget + 6:
                pool.terminate()
                inflight = []
        if not inflight and (over or not queue):
            break
        time.sleep(0.3)
    pool.terminate(); pool.join()
    remaining = len(tasks) - done - failed
    tag = "ALL_DONE" if remaining <= 0 and failed == 0 else "PARTIAL"
    print(f"{tag} done={done} fail={failed} remaining={remaining} "
          f"elapsed={time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
