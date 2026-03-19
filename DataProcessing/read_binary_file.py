import struct
import pandas as pd

def read_binary_log(file_path):
    record_format = '5f'
    record_size = struct.calcsize(record_format)
    
    data = []
    
    try:
        with open(file_path, 'rb') as f:
            while True:
                bytes_read = f.read(record_size)
                if not bytes_read or len(bytes_read) < record_size:
                    break
                
                record = struct.unpack(record_format, bytes_read)
                data.append(record)
                
        df = pd.DataFrame(data, columns=['Timestamp_ms', 'CH1_V', 'CH2_V', 'CH3_V', 'CH4_V'])
        return df

    except FileNotFoundError:
        print("File not found. Check the path.")
        return None

if __name__ == '__main__':
    file_number = 72
    df = read_binary_log(f'{file_number}.bin')
    if df is not None:
        print(df.head())
        df.to_csv(f'{file_number}_log_data.csv', index=False)