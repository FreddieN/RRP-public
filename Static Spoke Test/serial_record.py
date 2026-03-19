import serial
import csv
import time
import datetime
import threading
import sys
import statistics

PORT = "/dev/cu.usbserial-110"  
BAUD = 2000000
OUTPUT_FILE = "live_serial_data.csv"

is_running = True

try:
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2) 
    print(f"Connected to {PORT}")
except Exception as e:
    print(f"Error connecting to serial: {e}")
    sys.exit(1)

f = open(OUTPUT_FILE, "w", newline="")
csv_writer = csv.writer(f)
csv_writer.writerow(["timestamp", "ch1", "ch2", "ch3"])

def wait_for_key():
    global is_running
    input("Press Enter to stop recording...\n")
    is_running = False

# Background thread to listen for input so the main loop can record uninterrupted
threading.Thread(target=wait_for_key, daemon=True).start()

print("Recording data...")
print("Raw rate: ~30,000 Hz | Median window: 12 | Effective save rate: ~2,500 Hz")

try:
    # 30,000 Hz raw / 12 samples per median = 2,500 saved points per second
    # This allows capturing signals up to 1,000 Hz (Nyquist) with overhead
    buffer_ch1 = []
    buffer_ch2 = []
    buffer_ch3 = []
    MEDIAN_WINDOW = 12  # 30kHz / 12 = 2500 Hz effective save rate

    while is_running:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    v1, v2, v3 = float(parts[0]), float(parts[1]), float(parts[2])
                    
                    buffer_ch1.append(v1)
                    buffer_ch2.append(v2)
                    buffer_ch3.append(v3)
                    
                    # Every 12 raw readings, compute median and save
                    # This naturally produces 2500 Hz save rate from 30kHz raw
                    if len(buffer_ch1) >= MEDIAN_WINDOW:
                        med_v1 = statistics.median(buffer_ch1)
                        med_v2 = statistics.median(buffer_ch2)
                        med_v3 = statistics.median(buffer_ch3)
                        
                        t = datetime.datetime.now()
                        csv_writer.writerow([t, med_v1, med_v2, med_v3])
                        
                        buffer_ch1.clear()
                        buffer_ch2.clear()
                        buffer_ch3.clear()
                        
            except (ValueError, IndexError):
                pass
except KeyboardInterrupt:
    print("\nKeyboardInterrupt received. Stopping...")
finally:
    is_running = False
    ser.close()
    f.close()
    print("Files closed. Recording stopped.")