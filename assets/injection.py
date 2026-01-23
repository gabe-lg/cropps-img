import csv
import datetime
import sys
import time

try:
    import serial
except ModuleNotFoundError:
    print("Module serial not found.")

# Configuration (adjust as needed)
BAUD_RATE = 9600
CURRENT = 40e-6  # Constant current in Amps (e.g., 20 µA)
MEASUREMENT_TIME = 30  # Total time in seconds
SAMPLE_INTERVAL = 0.01  # Sampling interval in seconds
VOLT_COMPLIANCE = 200  # Voltage compliance in V

# Data storage
data = []


def main(port, duration, amplitude):
    # FIXME: use `duration` and `amplitude` instead of hardcoding
    # Initialize serial connection
    try:
        keithley = serial.Serial(
            port=port,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        time.sleep(1)  # Allow settling

        # Test communication
        keithley.write(b'*IDN?\n')
        time.sleep(0.1)
        response = keithley.readline().decode('utf-8').strip()
        print(f'Connected to: {response}')

        # Reset instrument
        keithley.write(b'*RST\n')
        time.sleep(1)

        # Configure for constant current mode
        commands = [
            b':SOUR:FUNC CURR',  # Set to current source
            f':SENS:VOLT:PROT {VOLT_COMPLIANCE}\n'.encode('utf-8'),
            # Voltage compliance
            b':SENS:VOLT:RANG:AUTO ON',  # Auto range voltage
            b':SENS:CURR:RANG:AUTO ON',  # Auto range current
            b':SENS:FUNC:CONC ON',  # Concurrent measurements
            b':SENS:FUNC "VOLT"',  # Sense voltage
            b':SENS:FUNC "CURR"',  # Sense current
            b':FORM:ELEM VOLT,CURR,TIME',  # Output format: V, I, time
            b':SOUR:DEL:AUTO ON',  # Auto delay
            b':TRIG:SOUR BUS',  # Bus trigger
            b':TRIG:COUN 1'  # Single measurement per read
        ]
        for cmd in commands:
            keithley.write(cmd + b'\n')
            time.sleep(0.1)

        # Set constant current level
        keithley.write(f':SOUR:CURR {CURRENT}\n'.encode('utf-8'))
        time.sleep(0.1)

        # Output ON
        keithley.write(b':OUTP ON\n')
        print(
            f'Output enabled. Constant current: {CURRENT * 1000:.3f} mA for {MEASUREMENT_TIME} seconds.')

        # Main measurement loop
        start_time = time.time()
        sample_count = 0
        num_samples = int(MEASUREMENT_TIME / SAMPLE_INTERVAL)
        print('Starting measurements... Press Ctrl+C to stop early.')

        try:
            while (time.time() - start_time) < MEASUREMENT_TIME:
                # Trigger read
                keithley.write(b':READ?\n')
                response = keithley.readline().decode('utf-8').strip()

                if response:
                    # Parse response: V,I,TIME (comma-separated)
                    parts = response.split(',')
                    if len(parts) >= 2:
                        voltage = float(parts[0])
                        current = float(parts[1])
                        timestamp = time.time() - start_time
                        data.append([timestamp, voltage, current])
                        sample_count += 1
                        if sample_count % 100 == 0:  # Progress every 100 samples
                            print(
                                f'Progress: {sample_count}/{num_samples} samples | V: {voltage:.3f}V | I: {current * 1000:.3f}mA')

                # Wait for next sample
                time.sleep(SAMPLE_INTERVAL)

        except KeyboardInterrupt:
            print('\nMeasurement interrupted by user.')

    except Exception as e:
        print(f'Serial error: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}')

    finally:
        # Cleanup: Output OFF
        if 'keithley' in locals() and keithley.is_open:
            keithley.write(b':OUTP OFF\n')
            time.sleep(0.1)
            keithley.close()
            print('Output disabled and connection closed.')

    # Save data to CSV if any collected
    if data:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'keithley_data_{timestamp}.csv'
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Time(s)', 'Voltage(V)', 'Current(A)'])
            writer.writerows(data)
        print(f'Data saved to: {filename}')
        print(f'Total samples: {len(data)}')
        print(
            f'Average voltage: {sum(row[1] for row in data) / len(data):.3f} V')
        print(
            f'Average current: {sum(row[2] for row in data) / len(data) * 1000:.3f} mA')
    else:
        print('No data collected.')

    print('Measurement complete!')
