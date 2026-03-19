import sys
import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pywt
from pathlib import Path

def main():
    folder_name = sys.argv[1]
    base_dir = Path(__file__).parent
    rotations_dir = base_dir / folder_name / "rotations"
        
    csv_files = sorted([f for f in os.listdir(rotations_dir) if f.endswith(".csv")])
        
    print(f"Found {len(csv_files)} segments for '{folder_name}'")
    
    channels = ['CH1_V', 'CH2_V', 'CH3_V', 'CH4_V']
    
    cols = len(csv_files)
    rows = len(channels)
    
    wavelet = 'db8'
    level = 5
    band_labels = [f'cA{level}'] + [f'cD{i}' for i in range(level, 0, -1)]
    
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows), sharex='col')
    fig.suptitle(f"Discrete Wavelet Transform ({wavelet}, level {level}): {folder_name}", fontsize=18, fontweight="bold", y=0.98)
    
    for c_idx, csv_file in enumerate(csv_files):
        df = pd.read_csv(str(rotations_dir / csv_file))
        
        t = df['Timestamp_ms'].values
        
        for r_idx, ch in enumerate(channels):
            ax = axes[r_idx, c_idx]
            
            if ch in df.columns:
                signal = df[ch].values
                signal = signal - np.mean(signal)
                
                coeffs = pywt.wavedec(signal, wavelet, level=level)
                
                n_bands = len(coeffs)
                for i, c in enumerate(coeffs):
                    band_power = c ** 2
                    band_t = np.linspace(t[0], t[-1], len(c) + 1)
                    band_y = np.array([i, i + 1])
                    im = ax.pcolormesh(band_t, band_y, band_power[np.newaxis, :],
                                       cmap='jet', shading='flat')
                
                ax.set_ylim(n_bands, 0)
                ax.set_xlim(t[0], t[-1])
                
                ax.set_yticks(range(len(coeffs)))
                ax.set_yticklabels(band_labels, fontsize=8)
                
                if c_idx == cols - 1:
                    plt.colorbar(im, ax=ax, pad=0.02, label='Power')
                
            if r_idx == 0:
                ax.set_title(csv_file.replace('.csv', ''), fontweight="bold")
            if c_idx == 0:
                ax.set_ylabel(f"{ch}\nBand", fontweight="bold")
            if r_idx == rows - 1:
                ax.set_xlabel("Time (ms)", fontweight="bold")
                
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    out_file = base_dir / folder_name / f"wavelet_grid_{folder_name}.png"
    plt.savefig(str(out_file), dpi=150, bbox_inches="tight")
    print(f"Saved wavelet grid plot to {out_file}")
    
if __name__ == "__main__":
    main()

