import time
import serial.tools.list_ports


# PORT = "/dev/ttyUSB0" # TTL converter
PORT = "/dev/tty.usbserial-A904QEI2"  # TTL converter


# ---------------------------    serial PORT: python -> c++     ----------------------------------------------
ser = serial.Serial(PORT)
print("PORT: "+PORT)
ser.baudrate = 9600

# ---------------------------     func that sends the data through serial  -----------------------------------

# sends the data and prints on the terminal


def serial_send(data):
    data = data.encode('ascii')
    print(data)
    ser.write(data)
    time.sleep(0.05)


while True:
    x = input("command: ")
    if x == "1":
        serial_send('a')
    if x == "2":
        serial_send('b')
    if x == "3":
        serial_send('c')
    if x == "4":
        serial_send('d')
        time.sleep(0.1)


# while True:
# x = input("command: ")
# if x == "1":
#     serial_send('a')
#     serial_send('b')


# for i in range(5):
#     serial_send('a')
#     serial_send('b')
