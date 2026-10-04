#!/usr/bin/env python3
"""Plot results/results.csv: one figure per workload (hit rate and worst
100-access window against the swept parameter) plus a summary at the default
configuration. Writes PNGs to results/plots/.

    python tools/plot_results.py [--csv results/results.csv] [--outdir results/plots]
"""
import argparse
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Reference palette, light mode: surface, ink tokens, categorical slots 1 and 2.
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834"]

TITLES = {
    "ring": "1. Sensor ring buffer (4 KB, 4 laps)",
    "movavg": "2. Moving-average filter (64-sample window)",
    "structs": "3. Array of structs vs struct of arrays",
    "traversal": "4. Row vs column traversal (64 x 64 table)",
    "conflict": "5. Conflict thrash (buffers 8 KB apart)",
    "coldstart": "6. Cold start vs steady state (6 KB table)",
}
PARAM_LABEL = {"ways": "Ways per set (64 sets, 32-byte lines)",
               "line_size": "Line size in bytes (64 sets, 4 ways)"}
DEFAULT_ROW = "ways == 4 and line_size == 32"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
})
plt.rcParams["axes.grid.axis"] = "y"


def style_axes(ax):
    ax.spines["left"].set_visible(False)
    ax.tick_params(length=0)


def plot_workload(df, name, outdir):
    sub = df[df.workload == name]
    param = sub.sweep_param.iloc[0]
    variants = list(dict.fromkeys(sub.variant))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, column, ylabel in [
            (axes[0], "hit_rate", "Hit rate"),
            (axes[1], "worst_window_cycles", "Worst 100-access window (cycles)")]:
        # Direct labels at the line ends, unless two ends are too close to read;
        # the legend always carries identity.
        ends = [sub[sub.variant == v].sort_values("sweep_value")[column].iloc[-1] for v in variants]
        span = sub[column].max() or 1
        crowded = any(abs(a - b) < 0.1 * span for k, a in enumerate(ends) for b in ends[k + 1:])
        for i, variant in enumerate(variants):
            s = sub[sub.variant == variant].sort_values("sweep_value")
            x = range(len(s))
            ax.plot(x, s[column], color=SERIES[i % 2], linewidth=2, marker="o", markersize=6.5,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, label=variant or name)
            if len(variants) > 1 and not crowded:
                ax.annotate(variant, (len(s) - 1, s[column].iloc[-1]), xytext=(8, 0),
                            textcoords="offset points", color=INK, va="center", fontsize=9)
        ax.set_xticks(list(range(len(s))))
        ax.set_xticklabels([str(v) for v in s.sweep_value])
        ax.set_xlabel(PARAM_LABEL[param])
        ax.set_ylabel(ylabel)
        ax.set_ylim(bottom=0)
        if column == "hit_rate":
            ax.set_ylim(0, 1.05)
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        else:
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
        ax.margins(x=0.12)
        style_axes(ax)
    if len(variants) > 1:
        axes[0].legend(frameon=False, loc="best", labelcolor=INK_2)
    fig.suptitle(TITLES[name], x=0.01, ha="left", fontweight="bold", fontsize=12, color=INK)
    fig.text(0.01, 0.01, "Cost model: hit 1 cycle, miss 100 cycles. Other parameters at defaults.",
             color=INK_2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path = outdir / f"{name}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_summary(df, outdir):
    d = df.query(DEFAULT_ROW).copy()
    d["label"] = [f"{w} ({v})" if v else w for w, v in zip(d.workload, d.variant)]
    d = d.iloc[::-1]  # first workload at the top
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    for ax, column, title, fmt in [
            (axes[0], "hit_rate", "Hit rate", lambda v: f"{v:.1%}"),
            (axes[1], "worst_window_cycles", "Worst 100-access window (cycles)", lambda v: f"{v:,.0f}")]:
        bars = ax.barh(d.label, d[column], color=SERIES[0], height=0.62)
        for bar, value in zip(bars, d[column]):
            ax.annotate(fmt(value), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0), textcoords="offset points", va="center", color=INK, fontsize=9)
        ax.set_title(title)
        ax.grid(axis="x")
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, d[column].max() * 1.18)
        ax.xaxis.set_major_formatter(
            (lambda v, _: f"{v:.0%}") if column == "hit_rate" else (lambda v, _: f"{v:,.0f}"))
        style_axes(ax)
        ax.spines["bottom"].set_visible(False)
    fig.suptitle("All workloads at the default cache (64 sets, 4 ways, 32-byte lines)",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = outdir / "summary.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=pathlib.Path, default=ROOT / "results" / "results.csv")
    parser.add_argument("--outdir", type=pathlib.Path, default=ROOT / "results" / "plots")
    args = parser.parse_args(argv)
    if not args.csv.exists():
        print(f"error: {args.csv} not found (run tools/run_experiments.py first)", file=sys.stderr)
        return 2
    df = pd.read_csv(args.csv, keep_default_na=False)
    args.outdir.mkdir(parents=True, exist_ok=True)
    paths = [plot_workload(df, name, args.outdir) for name in TITLES if name in set(df.workload)]
    paths.append(plot_summary(df, args.outdir))
    print("\n".join(str(p) for p in paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
