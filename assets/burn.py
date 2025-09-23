import time

import serial

# Configure serial port (replace 'COM3' with your Arduino's port)
SERIAL_PORT = 'COM4'  # Example: 'COM3' on Windows, '/dev/ttyUSB0' on Linux/Mac
BAUD_RATE = 9600


def main():
    try:
        # Initialize serial connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        print("Connected to Arduino on", SERIAL_PORT)

        # Read initial Arduino messages
        while ser.in_waiting:
            print(ser.readline().decode('utf-8').strip())

        # Send L1 command to Arduino
        ser.write('L1\n'.encode('utf-8'))
        print("Sent L1 command")

        # Read and display Arduino response
        time.sleep(0.1)  # Brief delay to allow Arduino to respond
        while ser.in_waiting:
            print(ser.readline().decode('utf-8').strip())

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nProgram interrupted.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed.")


if __name__ == "__main__":
    main()
