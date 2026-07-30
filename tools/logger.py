import sys
import time
import os
from datetime import datetime
import traceback

def log_can_bus():
    SERIAL_PORT = 'COM5'  # Updated to your active port
    BAUD_RATE = 921600
    
    # Bypass Windows 'Documents' folder restrictions by writing to the root C: drive
    LOG_DIR = r"C:\CAN_Logs"
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Could not create folder at {LOG_DIR}. Error: {e}")
            return
            
    timestamp_str = datetime.now().strftime('%H%M%S')
    OUTPUT_FILE = os.path.join(LOG_DIR, f'kcan_log_{timestamp_str}.txt')
    
    ser = None

    try:
        import serial
    except ModuleNotFoundError:
        print("\n[CRITICAL ERROR] The 'pyserial' library is not installed.")
        return

    try:
        print(f"Connecting to {SERIAL_PORT}...")
        
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        
        # Explicitly toggle DTR/RTS for ESP32-C3 Native USB
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        ser.dtr = True
        ser.rts = True
        
        print(f"Connected! Logging data to {OUTPUT_FILE}...")
        print("Press Ctrl+C to stop.")
        
        with open(OUTPUT_FILE, 'w') as file:
            file.write("Timestamp,ID,DLC,Data\n")
            
            while True:
                raw_data = ser.readline() 
                
                if raw_data:
                    try:
                        line = raw_data.decode('utf-8').strip()
                        if line:
                            current_time = datetime.now().strftime('%H:%M:%S')
                            print(f"[{current_time}] {line}")
                            file.write(f"{current_time},{line}\n")
                            file.flush()
                    except UnicodeDecodeError:
                        pass 
                        
    except serial.SerialException as e:
        print(f"\n[PORT ERROR] Could not connect to {SERIAL_PORT}.")
        print(f"Details: {e}")
    except KeyboardInterrupt:
        print(f"\nLogging stopped. Data saved to {OUTPUT_FILE}")
    except Exception as e:
        print("\n[UNKNOWN FATAL ERROR]")
        traceback.print_exc()
    finally:
        if ser and ser.is_open:
            ser.close()

if __name__ == '__main__':
    try:
        log_can_bus()
    except Exception as e:
        print(f"Critical launch failure: {e}")
    
    print("\n" + "="*40)
    input("Press Enter to close this window...")