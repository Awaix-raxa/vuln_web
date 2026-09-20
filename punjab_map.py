"""Choropleth map of Punjab, Pakistan population by district (2023 census).

Styled as an atlas sheet: neatline frame with a lat/lon graticule, a
locator inset, a compass rose, a segmented scale bar, and a marginalia
footer with source/projection/cartographer credits.

Boundary source: Pakistan COD-AB (OCHA/ITOS, valid as of 2022-09-09,
via HDX). It carries 36 of Punjab's 41 current districts as individual
polygons -- Chiniot and Mandi Bahauddin included, but five districts
notified in 2022 (Kot Addu, Murree, Talagang, Wazirabad, Taunsa) are not
yet split out and still sit inside their parent polygon. Every value
plotted or listed is the district's own exact 2023 census figure --
nothing is combined or estimated.
"""

import datetime
import json

import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Polygon as MplPolygon, Rectangle
from matplotlib.path import Path

ADM1_PATH = "/tmp/pak_adm/pak_admin1.geojson"
ADM2_PATH = "/tmp/pak_adm/pak_admin2.geojson"
CARTOGRAPHER = "Awais Raza"

PAGE = "#f4f3ee"
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
FRAME = "#3a3a36"
CONTEXT_FILL = "#e9e8e2"
CONTEXT_EDGE = "#cfcec5"
DISTRICT_EDGE = "#fcfcfb"
PROVINCE_EDGE = "#1a1a19"
LABEL_STROKE = "#0c1f3d"

BINS = [
    (1_500_000, "#b7d3f6", "< 1.5M"),
    (2_500_000, "#6da7ec", "1.5M – 2.5M"),
    (4_000_000, "#2a78d6", "2.5M – 4M"),
    (6_000_000, "#1c5cab", "4M – 6M"),
    (float("inf"), "#0d366b", "6M +"),
]

# Exact 2023 Digital Census population, one entry per district -- keyed
# to the boundary file's adm2_name. No merging, no estimates.
POPULATION = {
    "Attock": 2_170_423,
    "Bahawalnagar": 3_550_342,
    "Bahawalpur": 4_284_964,
    "Bhakkar": 1_957_470,
    "Chakwal": 1_734_854,
    "Chiniot": 1_563_024,
    "Dera Ghazi Khan": 3_393_705,
    "Faisalabad": 9_075_819,
    "Gujranwala": 4_966_338,
    "Gujrat": 3_219_375,
    "Hafizabad": 1_319_909,
    "Jhang": 3_065_639,
    "Jhelum": 1_382_308,
    "Kasur": 4_084_286,
    "Khanewal": 3_364_077,
    "Khushab": 1_501_089,
    "Lahore": 13_004_135,
    "Leiah": 2_102_386,          # census spelling: Layyah
    "Lodhran": 1_928_299,
    "Mandi Bahauddin": 1_829_486,
    "Mianwali": 1_798_268,
    "Multan": 5_362_305,
    "Muzaffargarh": 3_528_567,
    "Nankana Sahib": 1_634_871,
    "Narowal": 1_950_954,
    "Okara": 3_515_490,
    "Pakpattan": 2_136_170,
    "Rahim Yar Khan": 5_564_703,
    "Rajanpur": 2_381_049,
    "Rawalpindi": 5_745_964,
    "Sahiwal": 2_881_811,
    "Sargodha": 4_334_448,
    "Sheikhupura": 4_049_418,
    "Sialkot": 4_499_394,
    "Toba Tek Singh": 2_524_044,
    "Vehari": 3_430_421,
}

# Districts notified in 2022 that this boundary vintage does not carry as
# their own polygon -- still exact 2023 census figures, listed rather
# than mapped. (Taunsa's population was not separately published; its
# residents are counted within Dera Ghazi Khan's 3,393,705 above.)
NOT_MAPPED = [
    ("Murree", 372_947, "within Rawalpindi"),
    ("Talagang", 602_246, "within Chakwal"),
    ("Kot Addu", 1_486_758, "within Muzaffargarh"),
    ("Wazirabad", 993_412, "within Gujranwala"),
    ("Taunsa", None, "counted in Dera Ghazi Khan"),
]

DISPLAY_NAME = {
    "Dera Ghazi Khan": "D.G. Khan",
    "Rahim Yar Khan": "R.Y. Khan",
    "Toba Tek Singh": "T.T. Singh",
    "Mandi Bahauddin": "M. Bahauddin",
    "Leiah": "Layyah",
}


def bin_for(value):
    for threshold, color, label in BINS:
        if value < threshold:
            return color, label
    return BINS[-1][1], BINS[-1][2]


def polygon_to_path(rings):
    verts, codes = [], []
    for ring in rings:
        verts.extend(ring)
        codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 2) + [Path.CLOSEPOLY])
    return Path(verts, codes)


def add_geom(ax, geom, **kwargs):
    """Add a Polygon/MultiPolygon geojson geometry to ax as PathPatch(es)."""
    coords_list = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for rings in coords_list:
        ax.add_patch(PathPatch(polygon_to_path(rings), **kwargs))


def ring_area(coords):
    x = np.array([p[0] for p in coords])
    y = np.array([p[1] for p in coords])
    return abs((x[:-1] * y[1:] - x[1:] * y[:-1]).sum() / 2.0)


def label_halo(ax, x, y, text, fontsize, fontweight="bold", color="white", zorder=5):
    ax.annotate(
        text, (x, y), ha="center", va="center",
        fontsize=fontsize, fontweight=fontweight, color=color,
        linespacing=1.2, zorder=zorder, family="DejaVu Sans",
        path_effects=[pe.withStroke(linewidth=2.2, foreground=LABEL_STROKE)],
    )


def draw_compass(ax, cx, cy, size):
    ax.add_patch(plt.Circle((cx, cy), size * 1.55, facecolor=SURFACE,
                             edgecolor=INK_SECONDARY, linewidth=0.9, zorder=6))
    north = np.array([[cx, cy + size], [cx + size * 0.32, cy], [cx, cy - size * 0.18]])
    south = np.array([[cx, cy - size], [cx - size * 0.32, cy], [cx, cy - size * 0.18]])
    ax.add_patch(MplPolygon(north, closed=True, facecolor=INK_PRIMARY, edgecolor="none", zorder=7))
    ax.add_patch(MplPolygon(south, closed=True, facecolor=SURFACE, edgecolor=INK_PRIMARY,
                             linewidth=0.6, zorder=7))
    ax.annotate("N", (cx, cy + size * 1.28), ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=INK_PRIMARY, zorder=7)


def draw_scale_bar(ax, x0, y0, km_per_degree, seg_km=50, segments=4):
    seg_deg = seg_km / km_per_degree
    bar_h = seg_deg * 0.22
    for i in range(segments):
        color = INK_PRIMARY if i % 2 == 0 else SURFACE
        ax.add_patch(Rectangle((x0 + i * seg_deg, y0), seg_deg, bar_h,
                                facecolor=color, edgecolor=INK_PRIMARY,
                                linewidth=0.7, zorder=7))
    for i in range(segments + 1):
        ax.annotate(f"{i * seg_km}", (x0 + i * seg_deg, y0 - bar_h * 0.9),
                    ha="center", va="top", fontsize=7, color=INK_SECONDARY, zorder=7)
    ax.annotate("km", (x0 + segments * seg_deg + seg_deg * 0.35, y0 + bar_h * 0.5),
                ha="left", va="center", fontsize=7.5, color=INK_SECONDARY, zorder=7)


def draw_locator(ax, adm1_features, punjab_name="Punjab"):
    loc = ax.inset_axes([0.015, 0.685, 0.27, 0.27])
    loc.set_facecolor(SURFACE)
    all_x, all_y = [], []
    for feat in adm1_features:
        is_punjab = feat["properties"]["adm1_name"] == punjab_name
        color = "#2a78d6" if is_punjab else CONTEXT_FILL
        edge = "#0d366b" if is_punjab else CONTEXT_EDGE
        lw = 1.1 if is_punjab else 0.5
        add_geom(loc, feat["geometry"], facecolor=color, edgecolor=edge, linewidth=lw, zorder=2)
        rings = (feat["geometry"]["coordinates"] if feat["geometry"]["type"] == "Polygon"
                 else [r for poly in feat["geometry"]["coordinates"] for r in poly])
        for ring in rings:
            for lon, lat in ring:
                all_x.append(lon); all_y.append(lat)
    loc.set_xlim(min(all_x) - 0.5, max(all_x) + 0.5)
    loc.set_ylim(min(all_y) - 0.5, max(all_y) + 0.5)
    loc.set_aspect(1 / np.cos(np.radians(np.mean(all_y))))
    loc.set_xticks([]); loc.set_yticks([])
    for spine in loc.spines.values():
        spine.set_edgecolor(INK_SECONDARY); spine.set_linewidth(0.8)
    loc.set_title("Pakistan", fontsize=7.5, color=INK_SECONDARY, pad=2, fontstyle="italic")


def main():
    adm2 = json.load(open(ADM2_PATH))
    adm1 = json.load(open(ADM1_PATH))
    punjab_features = [f for f in adm2["features"] if f["properties"].get("adm1_name") == "Punjab"]
    punjab_outline = next(f for f in adm1["features"] if f["properties"]["adm1_name"] == "Punjab")
    context_features = [f for f in adm1["features"] if f["properties"]["adm1_name"] != "Punjab"]

    missing = sorted(set(POPULATION) - {f["properties"]["adm2_name"] for f in punjab_features})
    extra = sorted({f["properties"]["adm2_name"] for f in punjab_features} - set(POPULATION))
    assert not missing and not extra, (missing, extra)

    fig = plt.figure(figsize=(12.5, 16), facecolor=PAGE)
    ax = fig.add_axes([0.085, 0.10, 0.86, 0.775])
    ax.set_facecolor(SURFACE)

    # --- geographic context (neighbouring provinces, muted) ---
    for feat in context_features:
        add_geom(ax, feat["geometry"], facecolor=CONTEXT_FILL, edgecolor=CONTEXT_EDGE,
                 linewidth=0.6, zorder=1)
        cx, cy = feat["properties"].get("center_lon"), feat["properties"].get("center_lat")
        if cx is not None:
            ax.annotate(feat["properties"]["adm1_name"].upper(), (cx, cy), ha="center",
                        va="center", fontsize=8.5, color=INK_MUTED, style="italic", zorder=1.5)

    # --- district choropleth, every district labelled ---
    all_lons, all_lats = [], []
    for feat in punjab_features:
        name = feat["properties"]["adm2_name"]
        pop = POPULATION[name]
        color, _ = bin_for(pop)
        geom = feat["geometry"]
        add_geom(ax, geom, facecolor=color, edgecolor=DISTRICT_EDGE, linewidth=0.8, zorder=2)

        rings_list = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for rings in rings_list:
            for ring in rings:
                for lon, lat in ring:
                    all_lons.append(lon); all_lats.append(lat)

        cx, cy = feat["properties"]["center_lon"], feat["properties"]["center_lat"]
        disp = DISPLAY_NAME.get(name, name)
        label_halo(ax, cx, cy, f"{disp}\n{pop / 1e6:.1f}M", fontsize=6.6)

    # --- provincial outline on top, crisp neat boundary ---
    add_geom(ax, punjab_outline["geometry"], facecolor="none", edgecolor=PROVINCE_EDGE,
              linewidth=1.6, zorder=3)

    mean_lat = float(np.mean(all_lats))
    xmin, xmax = min(all_lons) - 0.35, max(all_lons) + 0.35
    ymin, ymax = min(all_lats) - 0.35, max(all_lats) + 0.35
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect(1 / np.cos(np.radians(mean_lat)))

    # --- graticule + neatline frame with coordinate ticks ---
    lon_ticks = np.arange(np.ceil(xmin), np.floor(xmax) + 1, 1.0)
    lat_ticks = np.arange(np.ceil(ymin), np.floor(ymax) + 1, 1.0)
    ax.set_xticks(lon_ticks)
    ax.set_yticks(lat_ticks)
    ax.set_xticklabels([f"{v:g}°E" for v in lon_ticks], fontsize=8, color=INK_SECONDARY)
    ax.set_yticklabels([f"{v:g}°N" for v in lat_ticks], fontsize=8, color=INK_SECONDARY)
    ax.tick_params(direction="out", length=4, color=FRAME, labelsize=8, pad=4)
    ax.grid(True, linestyle=(0, (1, 3)), linewidth=0.6, color="#8a8a86", alpha=0.5, zorder=0.5)
    for spine in ax.spines.values():
        spine.set_edgecolor(FRAME)
        spine.set_linewidth(1.2)

    # --- marginalia: locator, compass, scale bar, legend ---
    draw_locator(ax, adm1["features"])
    draw_compass(ax, xmax - 0.42, ymax - 0.55, size=0.22)

    km_per_degree = 111.320 * np.cos(np.radians(mean_lat))
    draw_scale_bar(ax, xmin + 0.25, ymin + 0.35, km_per_degree, seg_km=50, segments=4)

    legend_handles = [
        plt.Line2D([0], [0], marker="s", linestyle="", markersize=11,
                    markerfacecolor=c, markeredgecolor="none", label=lab)
        for _, c, lab in BINS
    ]
    legend = ax.legend(handles=legend_handles, title="POPULATION", loc="lower right",
                        frameon=True, fontsize=8.5, title_fontsize=8.5,
                        labelcolor=INK_SECONDARY, bbox_to_anchor=(0.995, 0.02),
                        borderpad=0.9, handletextpad=0.7)
    legend.get_frame().set_facecolor(SURFACE)
    legend.get_frame().set_edgecolor(INK_SECONDARY)
    legend.get_frame().set_linewidth(0.7)
    legend.get_title().set_color(INK_PRIMARY)
    legend.get_title().set_fontweight("bold")

    # --- header block (outside the neatline, like an atlas sheet) ---
    fig.text(0.085, 0.965, "PUNJAB", fontsize=32, fontweight="bold",
              family="DejaVu Serif", color=INK_PRIMARY, ha="left")
    fig.text(0.085, 0.940, "POPULATION BY DISTRICT — 2023 CENSUS, ALL 41 DISTRICTS", fontsize=12.5,
              family="DejaVu Serif", color=INK_SECONDARY, ha="left")
    fig.add_artist(plt.Line2D([0.085, 0.945], [0.928, 0.928], color=FRAME, linewidth=1.1,
                                transform=fig.transFigure))

    # --- footer marginalia ---
    today = datetime.date.today().strftime("%B %Y")
    not_mapped_line = "  ·  ".join(
        f"{n} {p:,}" if p else f"{n} n/a" for n, p, _ in NOT_MAPPED
    )
    footer_left = (
        "PROJECTION  Plate Carrée (geographic, WGS84)     "
        "BOUNDARIES  Pakistan COD-AB (OCHA/ITOS), valid 2022-09-09\n"
        "SOURCE  2023 Digital Census, Pakistan Bureau of Statistics\n"
        "NOT SEPARATELY MAPPED (2022 boundary vintage; exact 2023 population, counted within parent district above)\n"
        f"{not_mapped_line}"
    )
    fig.text(0.085, 0.060, footer_left, fontsize=7.6, color=INK_MUTED, ha="left", va="top",
              linespacing=1.7, family="monospace")
    fig.text(0.945, 0.060, f"CARTOGRAPHY\n{CARTOGRAPHER}\n{today}", fontsize=8.5,
              color=INK_PRIMARY, ha="right", va="top", linespacing=1.6, fontweight="bold")
    fig.add_artist(plt.Line2D([0.085, 0.945], [0.088, 0.088], color=FRAME, linewidth=1.1,
                                transform=fig.transFigure))

    fig.savefig("punjab_population_map.png", dpi=240, facecolor=PAGE)
    plt.close(fig)
    print("Saved punjab_population_map.png")
    print(f"Mapped {len(punjab_features)} districts exactly; "
          f"{len(NOT_MAPPED)} listed separately; "
          f"total named = {len(punjab_features) + len(NOT_MAPPED)}")


if __name__ == "__main__":
    main()
