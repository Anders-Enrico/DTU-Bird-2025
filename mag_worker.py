import time
import csv
import os
from datetime import datetime
import RPi.GPIO as GPIO
import ads8688

GPIO.setwarnings(False)

def run_adc(start_event, start_time, interval, max_duration):
    base_folder = "/media/bird/D0E44DDBE44DC506/mag"
    folder = os.path.join(base_folder, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, "adc_data.csv")

    adc = ads8688.ADS8688(bus=0, device=1, cs_pin=8, freq=100000)
    adc.reset()
    adc.setGlobalRange(ads8688.R0)

    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "X", "Y", "Z"])
        print("[ADC] Initialized. Waiting for start...")
        start_event.wait()
        base_time = start_time.value
        print(f"[ADC] Starting at: {time.ctime(base_time)}")

        while True:
            now = time.time()
            if max_duration.value > 0 and now - base_time >= max_duration.value:
                print("[ADC] Max duration reached.")
                break

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            # X on bird is -y(-CH1)
            adc.manualChannel(1)
            x = -adc.raw2volt(adc.noOp(), ads8688.R0) * 10000
            # Y on bird is +z (+CH2)
            adc.manualChannel(2)
            y = adc.raw2volt(adc.noOp(), ads8688.R0) * 10000
            # Z on birdd is +x (+CH0)
            adc.manualChannel(0)
            z = adc.raw2volt(adc.noOp(), ads8688.R0) * 10000

            writer.writerow([timestamp, x, y, z])
            file.flush()
            print(f"[ADC] {timestamp}: X={x}, Y={y}, Z={z}")

            time.sleep(interval.value)
    
