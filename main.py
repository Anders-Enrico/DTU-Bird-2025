import multiprocessing
from multiprocessing import Process, Event, Value
from ctypes import c_double
import time
import signal
import os
import RPi.GPIO as GPIO
from camera_worker import run_camera
from mag_worker import run_adc
from spatial_worker import run_spatial, wait_for_satellites
import serial
import math as m

# === Config ===
INTERVAL_SECONDS = 1.0  # sample interval
MAX_DURATION_SECONDS = 0
SHUTDOWN_PIN = 20
LED_PIN = 21
USB_REQUIRED = 1  # 1 for LED to fade in/out and 0 to ignore and save to desktop if USB not connected
USB_PATH = "/media/bird/D0E44DDBE44DC506"
SERIAL_PORT = "/dev/ttyUSB0"

def blink_led(blink_interval, stop_event):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    while not stop_event.is_set():
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(blink_interval)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(blink_interval)

def fade_led_forever():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    pwm = GPIO.PWM(LED_PIN, 100)
    pwm.start(0)
    try:
        while True:
            for i in range(100):
                pwm.ChangeDutyCycle(50 * (1 + m.sin(i * 0.0628)))
                time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        pwm.stop()

def check_usb_and_serial():
    usb_ok = os.path.ismount(USB_PATH)
    serial_ok = os.path.exists(SERIAL_PORT)

    if USB_REQUIRED and (not usb_ok or not serial_ok):
        print("[Main] USB or serial connection missing. Fading LED indefinitely...")
        fade_led_forever()

    if not usb_ok:
        print("[Main] WARNING: USB not mounted. Using Desktop as fallback.")
    if not serial_ok:
        print("[Main] WARNING: Serial device not found.")

def wait_for_short_press():
    print("[Main] Waiting for button press to start logging...")
    while True:
        if GPIO.input(SHUTDOWN_PIN) == GPIO.LOW:
            start = time.time()
            while GPIO.input(SHUTDOWN_PIN) == GPIO.LOW:
                time.sleep(0.01)
            if time.time() - start < 1.5:
                print("[Main] Short press detected. Starting logging...")
                return
        time.sleep(0.1)

def wait_for_shutdown_button(shutdown_event):
    print("[Main] Monitoring shutdown button (hold 3s)...")
    while not shutdown_event.is_set():
        if GPIO.input(SHUTDOWN_PIN) == GPIO.LOW:
            start = time.time()
            while GPIO.input(SHUTDOWN_PIN) == GPIO.LOW:
                held_time = time.time() - start
                if held_time >= 10:
                    print("[Main] Reboot requested.")
                    for _ in range(3):
                        GPIO.output(LED_PIN, GPIO.HIGH)
                        time.sleep(0.2)
                        GPIO.output(LED_PIN, GPIO.LOW)
                        time.sleep(0.2)
                    os.system("sudo reboot")
                    return
                elif held_time >= 3:
                    print("[Main] Shutdown button held. Exiting...")
                    shutdown_event.set()
                    return
                time.sleep(0.1)
        time.sleep(0.1)

def launch_workers(start_event, start_time, sample_interval, max_duration):
    processes = [
        Process(target=run_camera, args=(start_event, start_time, sample_interval, max_duration)),
        Process(target=run_adc, args=(start_event, start_time, sample_interval, max_duration)),
        Process(target=run_spatial, args=(start_event, start_time, sample_interval, max_duration))
    ]
    for p in processes:
        p.start()
    time.sleep(2)
    start_time.value = time.time()
    start_event.set()
    print(f"[Main] Workers started at {time.ctime(start_time.value)}")
    return processes

def main():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SHUTDOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(LED_PIN, GPIO.OUT)

    while True:
        led_stop_event = Event()
        led_process = Process(target=blink_led, args=(1, led_stop_event))
        led_process.start()

        wait_for_short_press()

        # ✅ Check for USB and serial AFTER the button is pressed
        check_usb_and_serial()

        led_stop_event.set()
        led_process.join()
        GPIO.output(LED_PIN, GPIO.LOW)

        shutdown_event = Event()
        start_event = Event()
        start_time = Value(c_double, 0.0)
        sample_interval = Value(c_double, INTERVAL_SECONDS)
        max_duration = Value(c_double, MAX_DURATION_SECONDS)

        shutdown_watch = Process(target=wait_for_shutdown_button, args=(shutdown_event,))
        shutdown_watch.start()

        print("[Main] Monitoring shutdown button (hold 3s)...")

        sat_led_stop = Event()
        sat_blink_process = Process(target=blink_led, args=(0.25, sat_led_stop))
        sat_blink_process.start()

        print("[Main] Waiting for satellites...")

        sat_ready_event = Event()
        sat_count = Value("i", 0)
        sat_process = Process(target=wait_for_satellites, args=(sat_ready_event, sat_count, shutdown_event))
        sat_process.start()

        timeout = 30
        start_time_sat = time.time()

        while time.time() - start_time_sat < timeout:
            if shutdown_event.is_set():
                print("[Main] Shutdown requested during satellite wait.")
                break
            if sat_ready_event.is_set():
                print("[Main] Satellite lock acquired.")
                break
            time.sleep(0.1)

        sat_process.terminate()
        sat_process.join()
        sat_led_stop.set()
        sat_blink_process.join()

        if not sat_ready_event.is_set() or shutdown_event.is_set():
            print("[Main] Timeout or shutdown during satellite wait. Restarting loop.")
            shutdown_watch.terminate()
            while GPIO.input(SHUTDOWN_PIN) == GPIO.LOW:
                time.sleep(0.1)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(5)
            print("[Main] Ready for next session.")
            continue

        GPIO.output(LED_PIN, GPIO.HIGH)

        processes = launch_workers(start_event, start_time, sample_interval, max_duration)

        while not shutdown_event.is_set():
            time.sleep(0.5)

        print("[Main] Terminating workers...")
        for p in processes:
            p.terminate()
            p.join()

        shutdown_watch.terminate()
        GPIO.output(LED_PIN, GPIO.LOW)

        print("[Main] Cooling down before next session...")

        while GPIO.input(SHUTDOWN_PIN) == GPIO.LOW:
            time.sleep(0.1)

        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(5)

        print("[Main] Ready for next session.")

if __name__ == '__main__':
    main()
