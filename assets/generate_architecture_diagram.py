import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

fig, ax = plt.subplots(figsize=(13, 4))

stages = [
    ("Stage 1\nTransport\n(TCP / UDP / Serial)", "#c0392b"),
    ("Stage 2\nCAN Bus\n(SocketCAN / vcan0)", "#e67e22"),
    ("Stage 3\nJ1939\n(PGN / SPN / BAM)", "#16a085"),
    ("Stage 4\nRTOS\n(Zephyr / native_sim)", "#2c3e50"),
    ("Stage 5\nBenchmark Suite\n(CAN vs UDP vs TCP)", "#e0a13d"),
]

box_w, box_h = 2.1, 1.6
gap = 0.55
start_x = 0.3
y = 0.5

for i, (label, color) in enumerate(stages):
    x = start_x + i * (box_w + gap)
    rect = mpatches.FancyBboxPatch((x, y), box_w, box_h,
                                     boxstyle="round,pad=0.05,rounding_size=0.08",
                                     linewidth=1.5, edgecolor=color, facecolor=color, alpha=0.15)
    ax.add_patch(rect)
    ax.text(x + box_w/2, y + box_h/2, label, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=color)
    if i < len(stages) - 1:
        arrow = FancyArrowPatch((x + box_w, y + box_h/2), (x + box_w + gap, y + box_h/2),
                                  arrowstyle="-|>", mutation_scale=20, linewidth=1.8, color="#555")
        ax.add_patch(arrow)

ax.set_xlim(0, start_x + len(stages) * (box_w + gap))
ax.set_ylim(0, 2.6)
ax.axis("off")
ax.set_title("CAN-Net Architecture: Layered Build, Stage by Stage", fontsize=13, fontweight="bold", pad=15)

fig.tight_layout()
fig.savefig("assets/architecture_diagram.png", dpi=150, bbox_inches="tight")
print("Saved assets/architecture_diagram.png")
