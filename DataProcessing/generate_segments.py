import sys
import os
import math
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from scipy.signal import find_peaks, butter, filtfilt
from read_binary_file import read_binary_log

def main():
    folder_name = sys.argv[1]
    base_dir = Path(__file__).parent
    folder_path = base_dir / folder_name / "data"
        
    rotations_dir = base_dir / folder_name / "rotations"
    rotations_dir.mkdir(parents=True, exist_ok=True)
        
    bin_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".bin")])
        
    print(f"Found {len(bin_files)} recordings for '{folder_name}'")
    
    channels = ['CH1_V', 'CH2_V', 'CH3_V', 'CH4_V']
    colors = plt.cm.tab10.colors
    
    all_segments = []
    
    for bin_file in bin_files:
        bin_base = bin_file.replace('.bin', '')
        df = read_binary_log(str(folder_path / bin_file))
        
        if df is None or df.empty or 'CH4_V' not in df.columns:
            continue
            
        t = df['Timestamp_ms']
        ch4_data = df['CH4_V'].values
        t_vals = t.values
        
        dt_sec = (t_vals[-1] - t_vals[0]) / 1000.0 / len(t_vals)
        fs = 1.0 / dt_sec if dt_sec > 0 else 20.0
        
        # Low-pass filter at 1.0 Hz
        cutoff = 1.0
        nyq = 0.5 * fs
        normal_cutoff = min(cutoff / nyq, 0.99)
        b, a = butter(2, normal_cutoff, btype='low', analog=False)
        ch4_filtered = filtfilt(b, a, ch4_data)
        
        distance_samples = int(2.0 * fs)
        peaks, _ = find_peaks(ch4_filtered, distance=distance_samples, prominence=0.002)
        
        for i in range(len(peaks) - 1):
            start_idx = peaks[i]
            end_idx = peaks[i+1]
            segment_label = f"{bin_base}_seg{i}"
            
            segment_df = df.iloc[start_idx:end_idx].copy()
            if not segment_df.empty:
                segment_df['Timestamp_ms'] = segment_df['Timestamp_ms'] - segment_df['Timestamp_ms'].iloc[0]
            
            csv_path = rotations_dir / f"{segment_label}.csv"
            segment_df.to_csv(csv_path, index=False)
            
            all_segments.append({
                'label': segment_label,
                'df': segment_df
            })
            
    print(f"Extracted a total of {len(all_segments)} rotation segments.")
    if not all_segments:
        print("No segments generated. Could not find enough peaks.")
        sys.exit(0)
        
    n_segs = len(all_segments)
    cols = 4 if n_segs >= 4 else n_segs
    rows = math.ceil(n_segs / cols)
    
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows), sharey=True)
    fig.suptitle(f"Rotation Segments: {folder_name}", fontsize=18, fontweight="bold", y=0.98)
    
    if rows == 1 and cols == 1:
        axes = [axes]
    elif rows == 1 or cols == 1:
        axes = list(axes)
    else:
        axes = [ax for row in axes for ax in row]
        
    for idx, seg in enumerate(all_segments):
        ax = axes[idx]
        seg_df = seg['df']
        t_seg = seg_df['Timestamp_ms']
        
        for j, ch in enumerate(channels):
            if ch in seg_df.columns:
                ax.plot(t_seg, seg_df[ch], label=ch, color=colors[j % len(colors)], alpha=0.9)
                
        ax.set_title(seg['label'], fontweight="bold")
        ax.grid(True, linestyle='--', alpha=0.6)
        
        if idx == 0:
            ax.legend(loc='lower right', fontsize='small')
            
    for ax in axes[-cols:]:
        ax.set_xlabel("Time Segment (ms)", fontweight="bold")
    for ax in axes[::cols]:
        ax.set_ylabel("Voltage (V)", fontweight="bold")
        
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    out_file = base_dir / folder_name / f"segments_grid_{folder_name}.png"
    plt.savefig(str(out_file), dpi=150, bbox_inches="tight")
    print(f"Saved segments grid plot to {out_file}")
    
if __name__ == "__main__":
    main()
