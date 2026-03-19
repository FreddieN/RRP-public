import os
import math
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path

DATA_DIR = Path(__file__).parent

folders = []
for entry in sorted(os.listdir(DATA_DIR)):
    folder_path = DATA_DIR / entry
    if folder_path.is_dir() and not (entry == "__pycache__" or entry == "_do_not_use"):
        data_dir = folder_path / "data"
        if data_dir.exists():
            data_files = sorted(f for f in os.listdir(data_dir) if not f.startswith("."))
        else:
            data_files = []
        folders.append({
            "name": entry,
            "img_path": str(folder_path / "img.png") if (folder_path / "img.png").exists() else None,
            "data_files": data_files,
        })

def get_min_bin_num(folder):
    nums = []
    for f in folder["data_files"]:
        if f.endswith(".bin"):
            try:
                nums.append(int(f.replace(".bin", "")))
            except ValueError:
                pass
    return min(nums) if nums else float('inf')

folders.sort(key=get_min_bin_num)

n = len(folders)
cols = 3
rows = 4

fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 6 * rows))
fig.suptitle("Wheel Strain Test — Labelled Data", fontsize=28, fontweight="bold", y=0.98)

if rows == 1:
    axes = [axes] if cols == 1 else list(axes)
else:
    axes = [ax for row in axes for ax in row]

for idx, folder in enumerate(folders):
    ax = axes[idx]
    if folder["img_path"]:
        img = mpimg.imread(folder["img_path"])
        ax.imshow(img)
    else:
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, fc="#e0e0e0", ec="none"))
        ax.text(0.5, 0.5, "No Image", transform=ax.transAxes, ha="center", va="center", color="#888888", fontsize=15, fontweight="bold")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect(1.0)
        
    ax.set_title(folder["name"], fontsize=25, fontweight="bold", pad=10)
    ax.axis("off")

    file_list = ", ".join(folder["data_files"]) if folder["data_files"] else "(no data files)"
    ax.text(
        0.5, -0.02, file_list,
        transform=ax.transAxes,
        ha="center", va="top",
        fontsize=18, color="gray",
        wrap=True,
    )

for idx in range(n, len(axes)):
    axes[idx].axis("off")

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(str(DATA_DIR / "grid_plot.png"), dpi=150, bbox_inches="tight")
print(f"Saved ({n} tiles)")
plt.show()
