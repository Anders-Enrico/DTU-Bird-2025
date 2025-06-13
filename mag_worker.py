import time
import csv
import os
from datetime import datetime
import RPi.GPIO as GPIO
import ads8688

GPIO.setwarnings(False)  # Disable GPIO warnings

# Main ADC logging function
def run_adc(start_event, start_time, interval, max_duration):
    # Create folder structure for data storage
    base_folder = "/media/bird/D0E44DDBE44DC506/mag"
    folder = os.path.join(base_folder, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, "adc_data.csv")

    # Initialize ADC with SPI settings
    adc = ads8688.ADS8688(bus=0, device=1, cs_pin=8, freq=100000)
    adc.reset()
    adc.setGlobalRange(ads8688.R0)

    # Open CSV file for writing
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "X", "Y", "Z"])  # Write header row
        print("[ADC] Initialized. Waiting for start...")

        # Wait for external start signal
        start_event.wait()
        base_time = start_time.value
        print(f"[ADC] Starting at: {time.ctime(base_time)}")

        while True:
            now = time.time()

            # Check if maximum logging duration has been reached
            if max_duration.value > 0 and now - base_time >= max_duration.value:
                print("[ADC] Max duration reached.")
                break

            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Read X-axis (Bird coordinate: -Y, connected to Channel 1)
            adc.manualChannel(1)
            x = -adc.raw2volt(adc.noOp(), ads8688.R0) * 10000

            # Read Y-axis (Bird coordinate: +Z, connected to Channel 2)
            adc.manualChannel(2)
            y = adc.raw2volt(adc.noOp(), ads8688.R0) * 10000

            # Read Z-axis (Bird coordinate: -X, connected to Channel 0)
            adc.manualChannel(0)
            z = -adc.raw2volt(adc.noOp(), ads8688.R0) * 10000

            # Write data to CSV and flush buffer
            writer.writerow([timestamp, x, y, z])
            file.flush()

            # Print measurement to console
            print(f"[ADC] {timestamp}: X={x}, Y={y}, Z={z}")

            # Wait for next sample interval
            time.sleep(interval.value)
