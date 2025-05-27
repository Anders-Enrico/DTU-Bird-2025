import datetime
import time
import math
import csv
import os
import an_devices.spatial_device as spatial_device
from anpp_packets.an_packet_protocol import ANPacket
from anpp_packets.an_packets import PacketID

def wait_for_satellites(sat_ready_event, sat_count, shutdown_event):
    comport = "/dev/ttyUSB0"
    baudrate = "460800"
    spatial = spatial_device.Spatial(comport, int(baudrate))

    if not spatial.is_open:
        print("[Spatial] Serial not open.")
        return

    spatial.flush()
    spatial.set_sensor_ranges(True,
        spatial_device.AccelerometerRange.accelerometer_range_4g,
        spatial_device.GyroscopeRange.gyroscope_range_500dps,
        spatial_device.MagnetometerRange.magnetometer_range_8g)

    spatial.get_device_and_configuration_information()
    spatial.request_packet(PacketID.satellites)

    print("[Spatial] Waiting for >5 satellites...")

    while not sat_ready_event.is_set() and not shutdown_event.is_set():
        if spatial.ser and spatial.ser.is_open and spatial.in_waiting() > 0:
            data = spatial.read(spatial.in_waiting())
            spatial.decoder.add_data(packet_bytes=data)

        if len(spatial.decoder.buffer) > 0:
            pkt = spatial.decoder.decode()
            if pkt and pkt.id == PacketID.satellites:
                sp = spatial_device.SatellitesPacket()
                if sp.decode(pkt) == 0:
                    total = (
                        sp.gps_satellites + sp.glonass_satellites +
                        sp.beidou_satellites + sp.galileo_satellites +
                        sp.sbas_satellites
                    )
                    sat_count.value = total
                    print(f"[Spatial] Satellites: {total}")
                    if total >= 5:
                        print("[Spatial] Satellite lock acquired.")
                        sat_ready_event.set()
        time.sleep(0.1)

def run_spatial(start_event, start_time, interval, max_duration, shutdown_event):
    comport = "/dev/ttyUSB0"
    baudrate = "460800"
    spatial = spatial_device.Spatial(comport, int(baudrate))

    if not spatial.is_open:
        print("[Spatial] Not connected.")
        return

    base_folder = "/media/bird/LOGGER1/spatial"
    folder = os.path.join(base_folder, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(folder, exist_ok=True)
    csv_path = os.path.join(folder, "spatial_log.csv")
    
    try:
        csv_file = open(csv_path, "w", newline="")
        writer = csv.writer(csv_file)
        writer.writerow(['timestamp', 'latitude', 'longitude', 'height', 'roll', 'pitch', 'satellites'])

        start_event.wait()
        base_time = start_time.value
        print(f"[Spatial] Logging started at: {time.ctime(base_time)}")

        last_log = 0.0
        while spatial.is_open and not shutdown_event.is_set():
            now = time.time()
            if max_duration.value > 0 and now - base_time >= max_duration.value:
                print("[Spatial] Max duration reached.")
                break

            if spatial.ser and spatial.ser.is_open and spatial.in_waiting() > 0:
                data = spatial.read(spatial.in_waiting())
                spatial.decoder.add_data(packet_bytes=data)

            if len(spatial.decoder.buffer) > 0:
                pkt = spatial.decoder.decode()
                if pkt and pkt.id == PacketID.system_state:
                    state = spatial_device.SystemStatePacket()
                    if state.decode(pkt) != 0:
                        print("[Spatial] Failed to decode system_state packet.")
                        continue

                    if (now - last_log) >= interval.value:
                        lat = math.degrees(state.latitude)
                        lon = math.degrees(state.longitude)
                        roll = math.degrees(state.orientation[0])
                        pitch = math.degrees(state.orientation[1])
                        timestamp = datetime.datetime.now().isoformat()

                        writer.writerow([timestamp, lat, lon, state.height, roll, pitch, ""])
                        csv_file.flush()
                        print(f"[Spatial] {timestamp}: Lat {lat:.6f} Lon {lon:.6f} Height {state.height:.2f} Roll {roll:.2f} Pitch {pitch:.2f}")
                        last_log = now
    finally:
        csv_file.close()
        spatial.close()
        print(f"[Spatial] Data saved to {csv_path}")
