import serial
import csv
import time
import datetime
import sys
import numpy as np
import pandas as pd
import sounddevice as sd
from scipy.signal import square
import statistics
import matplotlib.pyplot as plt

PORT = "/dev/cu.usbserial-110"  
BAUD = 2000000
OUTPUT_FILE = "combined_data.csv"

def run_sweep_and_record(f_start=0, f_end=500, duration=20, fs=44100):
    f_start = 100
    f_end = 100
    print(f"Generating square wave sweep from {f_start}Hz to {f_end}Hz for {duration} seconds...")
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    freqs = np.linspace(f_start, f_end, len(t))
    phase = 2 * np.pi * np.cumsum(freqs) / fs
    amplitude = square(phase).astype(np.float32)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        time.sleep(2)  # Wait for connection to establish
        print(f"Connected to {PORT}")
    except Exception as e:
        print(f"Error connecting to serial: {e}")
        sys.exit(1)

    ser.write(b"D")

    # Tare / Zero Calibration
    TARE_SAMPLES = 50
    tare_ch1 = []
    tare_ch2 = []
    tare_ch3 = []
    print(f"Calibrating sensors (collecting {TARE_SAMPLES} samples, keep sensors still)...")
    while len(tare_ch1) < TARE_SAMPLES:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    tare_ch1.append(float(parts[0]))
                    tare_ch2.append(float(parts[1]))
                    tare_ch3.append(float(parts[2]))
            except (ValueError, IndexError):
                pass
        else:
            time.sleep(0.0001)

    offset_ch1 = statistics.median(tare_ch1)
    offset_ch2 = statistics.median(tare_ch2)
    offset_ch3 = statistics.median(tare_ch3)
    print(f"Tare complete. Offsets: ch1={offset_ch1:.4f}, ch2={offset_ch2:.4f}, ch3={offset_ch3:.4f}")

    f = open(OUTPUT_FILE, "w", newline="")
    csv_writer = csv.writer(f)
    csv_writer.writerow(["timestamp", "time_elapsed", "frequency", "strain_gauge_2", "strain_gauge_1", "strain_gauge_3"])

    buffer_ch1 = []
    buffer_ch2 = []
    buffer_ch3 = []
    MEDIAN_WINDOW = 4  
    raw_line_count = 0  

    print("Starting playback and recording...")
    print(f"Median window: {MEDIAN_WINDOW} | Target save rate: ~2,500 Hz per channel")
    start_time_real = datetime.datetime.now()
    start_time_perf = time.perf_counter()

    # Start audio playback
    sd.play(amplitude, fs)

    recorded_data = []
    serial_buffer = b""  # Buffer for incoming serial bytes

    try:
        while True:
            elapsed_time = time.perf_counter() - start_time_perf
            
            if elapsed_time > duration:
                break

            waiting = ser.in_waiting
            if waiting > 0:
                serial_buffer += ser.read(waiting)
                
                while b"\n" in serial_buffer:
                    line_bytes, serial_buffer = serial_buffer.split(b"\n", 1)
                    try:
                        line = line_bytes.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        
                        parts = line.split()
                        if len(parts) >= 3:
                            v1, v2, v3 = float(parts[0]), float(parts[1]), float(parts[2])
                            raw_line_count += 1
                            
                            buffer_ch1.append(v1)
                            buffer_ch2.append(v2)
                            buffer_ch3.append(v3)
                            
                            if len(buffer_ch1) >= MEDIAN_WINDOW:
                                med_v1 = statistics.median(buffer_ch1) - offset_ch1
                                med_v2 = statistics.median(buffer_ch2) - offset_ch2
                                med_v3 = statistics.median(buffer_ch3) - offset_ch3
                                
                                current_dt = datetime.datetime.now()
                                current_freq = f_start + (f_end - f_start) * (elapsed_time / duration)

                                row = [current_dt, elapsed_time, current_freq, med_v1, med_v2, med_v3]
                                csv_writer.writerow(row)
                                recorded_data.append(row)
                                
                                buffer_ch1.clear()
                                buffer_ch2.clear()
                                buffer_ch3.clear()
                                
                    except (ValueError, IndexError):
                        pass
                
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt. Stopping early...")
        ser.write(b"s")
    finally:
        end_time_perf = time.perf_counter()
        sd.stop()
        ser.write(b"s")
        ser.close()
        f.close()
        actual_duration = end_time_perf - start_time_perf
    if recorded_data:
        print("Plotting results...")
        df = pd.DataFrame(recorded_data, columns=["timestamp", "time_elapsed", "frequency", "strain_gauge_2", "strain_gauge_1", "strain_gauge_3"])
        
        fig, ax1 = plt.subplots(figsize=(14, 7))

        color_freq = 'tab:red'
        ax1.set_xlabel('Time Elapsed (s)')
        ax1.set_ylabel('Frequency (Hz)', color=color_freq)
        ax1.plot(df['time_elapsed'], df['frequency'], color=color_freq, linewidth=2, label='Frequency', alpha=0.8)
        ax1.tick_params(axis='y', labelcolor=color_freq)

        ax2 = ax1.twinx()
        ax2.set_ylabel('Strain Gauge Amplitude')
        ax2.plot(df['time_elapsed'], df['strain_gauge_1'], label='Strain Gauge 1', alpha=0.7, linewidth=1)
        ax2.plot(df['time_elapsed'], df['strain_gauge_2'], label='Strain Gauge 2', alpha=0.7, linewidth=1)
        ax2.plot(df['time_elapsed'], df['strain_gauge_3'], label='Strain Gauge 3', alpha=0.7, linewidth=1)
        ax2.tick_params(axis='y')

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        all_lines = lines1 + lines2
        leg = ax1.legend(all_lines, labels1 + labels2, loc='upper left')

        lined = {}
        for legline, origline in zip(leg.get_lines(), all_lines):
            legline.set_picker(5)  # 5 pt tolerance
            lined[legline] = origline

        def on_pick(event):
            legline = event.artist
            origline = lined[legline]
            visible = not origline.get_visible()
            origline.set_visible(visible)
            legline.set_alpha(1.0 if visible else 0.2)
            fig.canvas.draw()

        fig.canvas.mpl_connect('pick_event', on_pick)

        ax1.set_title(f'Frequency Response ({f_start}Hz to {f_end}Hz Sweep)')
        ax1.grid(True, alpha=0.3)
        fig.tight_layout()
        
        plot_filename = 'frequency_response_plot.png'
        plt.savefig(plot_filename)
        print(f"Plot saved to '{plot_filename}'")
        print("Tip: Click legend entries to toggle lines on/off")
        plt.show()
    else:
        print("No data recorded to plot.")

if __name__ == "__main__":
    run_sweep_and_record(f_start=0, f_end=500, duration=20)
