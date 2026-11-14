#!/usr/bin/env python3
"""Автоматические замеры для лабораторной работы (оценка «3»).

Примеры:
  python run_bench.py calibrate                 # подобрать размеры (1 поток >= 10-20 с)
  python run_bench.py run --sizes 500 1000 2000 --logical 8 --physical 4
Результаты: results/raw.csv и results/meta.json
Замеряется только умножение: время печатает сама программа matmul (steady_clock),
прогресс при замерах отключён (6-й аргумент 0), чтобы печать не влияла на время.
"""
import argparse, csv, json, os, subprocess, sys, time

EXE = "matmul.exe" if os.name == "nt" else "./matmul"

def run_once(exe, n, T, order):
    out = subprocess.run([exe, str(n), str(n), str(n), str(T), order, "0"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        sys.exit(f"Ошибка запуска/проверки: {out.stdout}\n{out.stderr}")
    parts = [l for l in out.stdout.splitlines() if l.startswith("RESULT")][-1].split()
    return float(parts[6]), int(parts[7])

def thread_list(logical):
    ts = list(range(1, 2 * logical + 1))          # 1..2L с шагом 1
    ts += [4 * logical, 8 * logical]              # 4L и 8L
    return ts

def cmd_calibrate(a):
    print("Время одного запуска с 1 потоком (порядок itj). Нужен размер, где это 10-20 с.")
    for n in a.try_sizes:
        t, _ = run_once(a.exe, n, 1, "itj")
        print(f"  n={n}: {t:.2f} с")
        if t > 25: break

def cmd_run(a):
    os.makedirs(a.out, exist_ok=True)
    raw = os.path.join(a.out, "raw.csv")
    ts = thread_list(a.logical)
    sizes = sorted(a.sizes)
    json.dump({"sizes": sizes, "logical": a.logical, "physical": a.physical,
               "threads": ts, "reps": a.reps, "cmp_reps": a.cmp_reps},
              open(os.path.join(a.out, "meta.json"), "w"), indent=2)
    jobs = [(n, T, "itj", r) for n in sizes for T in ts for r in range(a.reps)]
    big = sizes[-1]
    jobs += [(big, 1, o, r) for o in ("ijt", "itj") for r in range(a.cmp_reps)]
    with open(raw, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["size", "threads", "order", "rep", "time_s", "checksum"])
        start = time.time()
        # прогрев: один неучитываемый запуск
        run_once(a.exe, sizes[0], 1, "itj")
        for idx, (n, T, o, r) in enumerate(jobs, 1):
            t, cs = run_once(a.exe, n, T, o)
            w.writerow([n, T, o, r, f"{t:.6f}", cs]); f.flush()
            el = time.time() - start
            print(f"[{idx}/{len(jobs)}] n={n} T={T} {o} rep={r}: {t:.3f} с  (прошло {el/60:.1f} мин)", flush=True)
    print("Готово ->", raw)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("calibrate"); c.add_argument("--exe", default=EXE)
    c.add_argument("--try-sizes", type=int, nargs="+", default=[500, 1000, 1500, 2000, 2500, 3000, 4000])
    c.set_defaults(f=cmd_calibrate)
    r = sp.add_parser("run"); r.add_argument("--exe", default=EXE)
    r.add_argument("--sizes", type=int, nargs=3, required=True)
    r.add_argument("--logical", type=int, required=True)
    r.add_argument("--physical", type=int, required=True)
    r.add_argument("--reps", type=int, default=5)
    r.add_argument("--cmp-reps", type=int, default=5, help="замеров для сравнения порядка циклов")
    r.add_argument("--out", default="results")
    r.set_defaults(f=cmd_run)
    a = p.parse_args(); a.f(a)
