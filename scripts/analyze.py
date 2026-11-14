#!/usr/bin/env python3
"""Обработка results/raw.csv: усреднение (без min и max), S(T), E(T), графики, таблицы.
Запуск: python analyze.py     (нужны pandas и matplotlib: pip install pandas matplotlib)
Выход: results/summary.csv, results/tables.md, results/*.png
"""
import json, os, sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = sys.argv[1] if len(sys.argv) > 1 else "results"
meta = json.load(open(os.path.join(OUT, "meta.json")))
raw = pd.read_csv(os.path.join(OUT, "raw.csv"))
L, P = meta["logical"], meta["physical"]

def trimmed(s):
    v = sorted(s)
    if len(v) >= 5: v = v[1:-1]       # отбрасываем наибольшее и наименьшее
    return sum(v) / len(v)

# основной эксперимент — первые строки (до блока сравнения порядков)
n_main = len(meta["sizes"]) * len(meta["threads"]) * meta["reps"]
main = raw.iloc[:n_main]
cmp_ = raw.iloc[n_main:]

g = main.groupby(["size", "threads"]).time_s.apply(trimmed).reset_index(name="time")
t1 = g[g.threads == 1].set_index("size").time
g["speedup"] = g.apply(lambda r: t1[r["size"]] / r.time, axis=1)
g["eff"] = g.speedup / g.threads
g.to_csv(os.path.join(OUT, "summary.csv"), index=False)

def style(ax, title, ylabel):
    ax.set_title(title); ax.set_xlabel("Число потоков T"); ax.set_ylabel(ylabel)
    ax.set_xscale("log", base=2)
    ticks = sorted(set([1, 2, 4, 8, P, L, 2 * L, 4 * L, 8 * L]))
    ax.set_xticks(ticks); ax.set_xticklabels([str(t) for t in ticks])
    ax.grid(True, alpha=.3)

def vlines(ax):
    ax.axvline(P, color="gray", ls="--", label=f"физ. ядра = {P}")
    ax.axvline(L, color="black", ls=":", label=f"лог. процессоры = {L}")

sizes = meta["sizes"]
fig, ax = plt.subplots(figsize=(8, 5))
for n in sizes:
    d = g[g["size"] == n]; ax.plot(d.threads, d.time, "o-", label=f"{n}×{n}")
vlines(ax); ax.set_yscale("log"); style(ax, "Время умножения от числа потоков", "Время, с (лог. шкала)"); ax.legend()
fig.savefig(os.path.join(OUT, "time.png"), dpi=150, bbox_inches="tight")

fig, ax = plt.subplots(figsize=(8, 5))
for n in sizes:
    d = g[g["size"] == n]; ax.plot(d.threads, d.speedup, "o-", label=f"{n}×{n}")
tt = sorted(g.threads.unique()); ax.plot([t for t in tt if t <= 2 * L], [t for t in tt if t <= 2 * L], "k-", alpha=.4, label="идеал S = T")
vlines(ax); ax.set_yscale("log", base=2)
style(ax, "Ускорение S(T) = t(1)/t(T)", "Ускорение (лог. шкала)"); ax.legend()
fig.savefig(os.path.join(OUT, "speedup.png"), dpi=150, bbox_inches="tight")

fig, ax = plt.subplots(figsize=(8, 5))
for n in sizes:
    d = g[g["size"] == n]; ax.plot(d.threads, d.eff, "o-", label=f"{n}×{n}")
vlines(ax); style(ax, "Эффективность E(T) = S(T)/T", "Эффективность"); ax.legend()
fig.savefig(os.path.join(OUT, "efficiency.png"), dpi=150, bbox_inches="tight")

# --- сравнение порядков циклов ---
cm = cmp_.groupby("order").time_s.apply(trimmed)
if len(cm) == 2:
    fig, ax = plt.subplots(figsize=(5, 4.5))
    labels = ["i→j→t (школьный)", "i→t→j"]; vals = [cm["ijt"], cm["itj"]]
    b = ax.bar(labels, vals, color=["tab:red", "tab:green"])
    for r, v in zip(b, vals): ax.text(r.get_x() + r.get_width() / 2, v, f"{v:.2f} с", ha="center", va="bottom")
    ax.set_title(f"Порядок циклов, 1 поток, {sizes[-1]}×{sizes[-1]}"); ax.set_ylabel("Время, с")
    fig.savefig(os.path.join(OUT, "loop_order.png"), dpi=150, bbox_inches="tight")

# --- таблицы и числа для отчёта ---
lines = []
for n in sizes:
    d = g[g["size"] == n]
    lines.append(f"\n### Размер {n}×{n}\n\n| Потоки | Среднее время, с | Ускорение | Эффективность |\n|---:|---:|---:|---:|")
    for _, r in d.iterrows():
        lines.append(f"| {int(r.threads)} | {r.time:.3f} | {r.speedup:.2f} | {r.eff:.2f} |")
lines.append("\n### Память под матрицы\n\n| Размер | Одна матрица, МБ | Три матрицы, МБ |\n|---:|---:|---:|")
for n in sizes:
    lines.append(f"| {n}×{n} | {n*n*8/2**20:.1f} | {3*n*n*8/2**20:.1f} |")
if len(cm) == 2:
    lines.append(f"\n### Порядок циклов (1 поток, {sizes[-1]}×{sizes[-1]})\n\n| Порядок | Время, с |\n|---|---:|\n| i→j→t | {cm['ijt']:.2f} |\n| i→t→j | {cm['itj']:.2f} |\n\nВыигрыш i→t→j: в {cm['ijt']/cm['itj']:.1f} раз.")
lines.append("\n### Ключевые числа для анализа\n")
for n in sizes:
    d = g[g["size"] == n].set_index("threads")
    best = d.time.idxmin()
    lin = max([t for t in d.index if t <= L and d.eff[t] >= 0.8] or [1])
    lines.append(f"- {n}×{n}: t(1) = {d.time[1]:.2f} с; минимум времени при T = {best} ({d.time[best]:.3f} с, S = {d.speedup[best]:.2f}); "
                 f"S({P}) = {d.speedup[P]:.2f}, S({L}) = {d.speedup[L]:.2f}, S({2*L}) = {d.speedup[2*L]:.2f}, "
                 f"S({8*L}) = {d.speedup[8*L]:.2f}; E>=0.8 до T = {lin}.")
open(os.path.join(OUT, "tables.md"), "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines)); print("\nГрафики и tables.md сохранены в", OUT)
