"""Hello world: build a small synthetic dataset with numpy/pandas and plot it."""

import matplotlib
import numpy as np

matplotlib.use("Agg")  # no GUI toolkit here; render straight to a file

import matplotlib.pyplot as plt
import pandas as pd

# Categorical slots 1-3 of the validated palette, assigned in fixed order.
SERIES_COLORS = {"North": "#2a78d6", "South": "#eb6834", "West": "#1baf7a"}
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
SURFACE = "#fcfcfb"


def make_dataset(seed: int = 7) -> pd.DataFrame:
    """Twelve months of synthetic revenue for three regions."""
    rng = np.random.default_rng(seed)
    months = pd.date_range("2026-01-01", periods=12, freq="MS")
    trends = {"North": 4.0, "South": 2.0, "West": -1.5}
    data = {
        region: 100 + slope * np.arange(12) + rng.normal(0, 4, 12)
        for region, slope in trends.items()
    }
    return pd.DataFrame(data, index=months)


def plot(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    for region in df.columns:
        color = SERIES_COLORS[region]
        ax.plot(df.index, df[region], color=color, linewidth=2, label=region,
                marker="o", markersize=6, markerfacecolor=color,
                markeredgecolor=SURFACE, markeredgewidth=2)
        # Direct label at the line end - identity is never color-alone.
        ax.annotate(region, (df.index[-1], df[region].iloc[-1]),
                    xytext=(8, 0), textcoords="offset points",
                    color=color, fontsize=10, fontweight="bold",
                    va="center")

    ax.set_title("Synthetic monthly revenue by region", color=INK_PRIMARY,
                 fontsize=14, pad=16, loc="left")
    ax.set_ylabel("Revenue (index)", color=INK_SECONDARY, fontsize=10)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)

    # Recessive grid and axes: the data is the loudest thing on the canvas.
    ax.grid(axis="y", color=INK_SECONDARY, alpha=0.15, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK_SECONDARY)
    ax.spines["bottom"].set_alpha(0.3)

    ax.legend(frameon=False, loc="upper left", ncols=3, fontsize=10,
              labelcolor=INK_SECONDARY, bbox_to_anchor=(0, -0.12))
    fig.tight_layout()
    fig.subplots_adjust(right=0.88)  # room for the end-of-line labels
    return fig


def main() -> None:
    df = make_dataset()
    print("Hello, world!\n")
    print(df.round(1).to_string())
    print(f"\nshape={df.shape}  mean={df.to_numpy().mean():.1f}")

    fig = plot(df)
    fig.savefig("revenue.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print("\nSaved chart to revenue.png")


if __name__ == "__main__":
    main()
