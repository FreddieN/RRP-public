import sys
import os
import matplotlib.pyplot as plt
from pathlib import Path
from read_binary_file import read_binary_log

def main():
    folder_name = sys.argv[1]
    base_dir = Path(__file__).parent 
    folder_path = base_dir / folder_name / "data"
        
    bin_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".bin")])
        
    print(f"Found {len(bin_files)} recordings for '{folder_name}': {bin_files}")
    
    channels = ['CH1_V', 'CH2_V', 'CH3_V', 'CH4_V']
    
    fig, axes = plt.subplots(len(bin_files), 1, figsize=(12, 4 * len(bin_files)), sharex=True)
    if len(bin_files) == 1:
        axes = [axes]
    fig.suptitle(f"Strain Gauge Recordings: {folder_name}", fontsize=16, fontweight="bold")
    
    colors = plt.cm.tab10.colors
    
    for i, bin_file in enumerate(bin_files):
        df = read_binary_log(str(folder_path / bin_file))
        if df is not None and not df.empty:
            t = df['Timestamp_ms']
            
            for j, ch in enumerate(channels):
                if ch in df.columns:
                    axes[i].plot(t, df[ch], label=ch, color=colors[j % len(colors)], alpha=0.8)
                    
            if 'CH4_V' in df.columns:
                from scipy.signal import find_peaks, butter, filtfilt
                ch4_data = df['CH4_V'].values
                t_vals = t.values
                
                dt_sec = (t_vals[-1] - t_vals[0]) / 1000.0 / len(t_vals)
                fs = 1.0 / dt_sec if dt_sec > 0 else 20.0 # fallback to ~20Hz
                
                cutoff = 1.0
                nyq = 0.5 * fs
                normal_cutoff = min(cutoff / nyq, 0.99) 
                b, a = butter(2, normal_cutoff, btype='low', analog=False)
                ch4_filtered = filtfilt(b, a, ch4_data)
                
                distance_samples = int(2.0 * fs) # minimum 2 seconds between peaks
                peaks, _ = find_peaks(ch4_filtered, distance=distance_samples, prominence=0.002)
                
                axes[i].plot(t.iloc[peaks], ch4_data[peaks], "go", label="Rotation Peak (CH4)", markersize=8, markeredgewidth=2, alpha=0.9)
            
            axes[i].set_title(bin_file, fontweight="bold")
            axes[i].set_ylabel("Voltage (V)")
            axes[i].grid(True, linestyle='--', alpha=0.6)
            if i == 0:
                axes[i].legend(loc='upper right', title="Channels")

    axes[-1].set_xlabel("Time (ms)", fontweight="bold")
    
    plt.tight_layout()
    
    out_file = base_dir / folder_name / f"{folder_name}_plot.png"
    plt.savefig(str(out_file), dpi=150, bbox_inches="tight")
    print(f"Saved plot to {out_file.name}")
    plt.show()

if __name__ == "__main__":
    main()
