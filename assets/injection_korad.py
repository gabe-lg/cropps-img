"""
Current-injection trigger path - KORAD KA6003P edition.

Drop-in replacement for assets/injection.py (the Keithley SMU path). Exposes the
same entry point:

    injection_korad.main(port)

so src/trigger.py can launch it in a daemon thread exactly like before.

Difference from the Keithley path
---------------------------------
The Keithley is a true *current source* (it forced 40 uA and rode the voltage up
to a 200 V compliance). The KA6003P is a *voltage source*: it holds a fixed
voltage while its own constant-current limit (ISET1) caps the current. The plant
is wired directly across the supply output - there is NO external series resistor
- so that ISET1 limit is the ONLY thing bounding the current into the plant. We
set a voltage, set the current limit, switch the output on/off (OUT1/OUT0 = the
trigger), and log the supply's measured V/I to CSV just like the old path did.

Protocol: KORAD KAxxxxP ASCII command set, 9600 baud 8N1, no line terminator,
~50 ms gap required between commands.
"""

import csv
import datetime
import time

try:
    import serial
except ModuleNotFoundError:
    print("Module serial not found.")

# ---------------------------------------------------------------------------
# Configuration (adjust as needed)
# ---------------------------------------------------------------------------
BAUD_RATE = 9600
VOLTAGE = 15.0          # Injection voltage in V (KA6003P range 0-60 V).
CURRENT_LIMIT = 0.001   # Supply current limit in A (1 mA). The plant is wired
                        # directly to the supply (no series resistor), so this
                        # constant-current limit is the ONLY thing capping the
                        # current into the plant. Set it to the maximum current
                        # the plant should ever see. Min settable step is 1 mA;
                        # use 0.002 for a 2 mA ceiling.
MEASUREMENT_TIME = 20   # Total injection time in seconds.
SAMPLE_INTERVAL = 0.25  # Seconds between samples. Each sample issues two serial
                        # queries; KORAD firmware needs ~50 ms/command, so keep
                        # this >= ~0.2 s (the old 0.01 s was for the Keithley).
CMD_GAP = 0.05          # Minimum gap between KORAD commands (firmware quirk).

# Data storage
data = []


def _write(ser, cmd):
    """Send one ASCII command (no terminator) and wait out the firmware gap."""
    ser.write(cmd.encode("ascii"))
    time.sleep(CMD_GAP)


def _query(ser, cmd, settle=CMD_GAP + 0.01, retries=4):
    """Send a query and return the ASCII reply.

    KORAD replies are short (e.g. '15.00') and carry NO line terminator, so a
    fixed ser.read(N) blocks the full serial timeout waiting for bytes that never
    arrive (~1 s wasted per query). Instead we wait a short settle, then read
    exactly what landed in the buffer -- returning in tens of ms per query.
    """
    ser.reset_input_buffer()
    ser.write(cmd.encode("ascii"))
    time.sleep(settle)
    for _ in range(retries):
        if ser.in_waiting:
            time.sleep(0.01)  # let the rest of the short reply land
            return ser.read(ser.in_waiting).decode("utf-8", errors="ignore").strip()
        time.sleep(0.02)
    return ""


def main(port):
    # Initialize serial connection
    try:
        korad = serial.Serial(
            port=port,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        time.sleep(1)  # Allow settling

        # Test communication
        response = _query(korad, "*IDN?")
        print(f"Connected to: {response}")

        # Make sure the output starts OFF, then program voltage + current cap.
        _write(korad, "OUT0")
        _write(korad, f"VSET1:{VOLTAGE:05.2f}")        # e.g. VSET1:15.00
        _write(korad, f"ISET1:{CURRENT_LIMIT:05.3f}")  # e.g. ISET1:0.001

        # Output ON - this is the injection trigger.
        _write(korad, "OUT1")
        print(
            f"Output enabled. {VOLTAGE:.2f} V, current-limited at "
            f"{CURRENT_LIMIT * 1000:.1f} mA, for {MEASUREMENT_TIME} seconds."
        )

        # Main measurement loop
        start_time = time.time()
        sample_count = 0
        num_samples = int(MEASUREMENT_TIME / SAMPLE_INTERVAL)
        print("Starting measurements... Press Ctrl+C to stop early.")

        try:
            while (time.time() - start_time) < MEASUREMENT_TIME:
                v_str = _query(korad, "VOUT1?")
                i_str = _query(korad, "IOUT1?")
                try:
                    voltage = float(v_str)
                    current = float(i_str)
                except ValueError:
                    # Occasional partial/garbled reply - skip this sample.
                    time.sleep(SAMPLE_INTERVAL)
                    continue

                timestamp = time.time() - start_time
                data.append([timestamp, voltage, current])
                sample_count += 1
                if sample_count % 20 == 0:  # Progress every 20 samples
                    print(
                        f"Progress: {sample_count}/{num_samples} samples | "
                        f"V: {voltage:.3f}V | I: {current * 1000:.3f}mA"
                    )

                time.sleep(SAMPLE_INTERVAL)

        except KeyboardInterrupt:
            print("\nMeasurement interrupted by user.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Cleanup: Output OFF (fail-safe - never leave the injection live).
        if "korad" in locals() and korad.is_open:
            _write(korad, "OUT0")
            korad.close()
            print("Output disabled and connection closed.")

    # Save data to CSV if any collected
    if data:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"korad_injection_data_{timestamp}.csv"
        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time(s)", "Voltage(V)", "Current(A)"])
            writer.writerows(data)
        print(f"Data saved to: {filename}")
        print(f"Total samples: {len(data)}")
        print(f"Average voltage: {sum(row[1] for row in data) / len(data):.3f} V")
        print(
            f"Average current: {sum(row[2] for row in data) / len(data) * 1000:.3f} mA"
        )
    else:
        print("No data collected.")

    print("Measurement complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m assets.injection_korad <PORT>   e.g. COM3 or /dev/ttyUSB0")
        sys.exit(1)
    main(sys.argv[1])
