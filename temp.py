from machine import Pin, ADC, PWM, I2C # type: ignore
import utime # type: ignore
import network # type: ignore
import ntptime # type: ignore
from notes import NOTES
from melody import MELODY
from utime import sleep # type: ignore
import ujson # type: ignore
import urequests # type: ignore
import framebuf # type: ignore

# SH1107 driver
class SH1107:
    def __init__(self, width=128, height=128, i2c=None, addr=0x3C, flip=False):
        self.width = width
        self.height = height
        self.pages = height // 8
        self.addr = addr
        self.i2c = i2c
        self.buffer = bytearray(self.pages * width)
        self.framebuf = framebuf.FrameBuffer(self.buffer, width, height, framebuf.MONO_VLSB)
        
        # Init commands for 128x128 SH1107
        self.init_cmds = bytes([
            0xAE,       # Display OFF
            0x02,       # Lower column address
            0x10,       # Higher column address
            0xB0,       # Page address
            0xDC, 0x00, # Display start line
            0x81, 0x80, # Contrast control (adjustable)
            0xA0,       # Segment remap (normal)
            0xC0,       # COM output scan direction (normal)
            0xA6,       # Normal display (not inverted)
            0xA8, 0x7F, # Multiplex ratio (128 rows)
            0xD3, 0x60, # Display offset
            0xD5, 0x51, # Display clock divide ratio/oscillator frequency
            0xD9, 0x22, # Pre-charge period
            0xDA, 0x12, # COM pins hardware configuration
            0xDB, 0x35, # VCOMH deselect level
            0x40,       # Display start line
            0xA4,       # Entire display ON (follow RAM)
            0xA6,       # Normal display (not inverted)
            0xAF        # Display ON
        ])
        
        if flip:  # Flip the display if requested
            self.init_cmds = bytes([
                0xAE, 0x02, 0x10, 0xB0, 0xDC, 0x00, 0x81, 0x80,
                0xA1,  # Segment remap (flipped horizontally)
                0xC8,  # COM output scan direction (flipped vertically)
                0xA6, 0xA8, 0x7F, 0xD3, 0x60, 0xD5, 0x51,
                0xD9, 0x22, 0xDA, 0x12, 0xDB, 0x35,
                0x40, 0xA4, 0xA6, 0xAF
            ])
        
        # Send initialization commands
        for cmd in self.init_cmds:
            self.write_cmd(cmd)
        
        self.fill(0)
        self.show()

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([0x00, cmd]))

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40' + buf)

    def fill(self, color):
        self.framebuf.fill(color)

    def text(self, text, x, y, color=1):
        self.framebuf.text(text, x, y, color)

    def show(self):
        for page in range(self.pages):
            self.write_cmd(0xB0 | page)  # Set page address
            self.write_cmd(0x02)         # Lower column address
            self.write_cmd(0x10)         # Higher column address
            self.write_data(self.buffer[page * self.width:(page + 1) * self.width])

# Hardware setup
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
oled = SH1107(128, 128, i2c)  # Initialize display

adc = ADC(Pin(26))  # Temperature sensor
buzzer = PWM(Pin(18))       
buzzer.duty_u16(0)  # Start with buzzer off

# Network Config
WIFI_SSID = "Google Björkgatan"
WIFI_PASSWORD = "wash@xidi"
UBIDOTS_TOKEN = "BBUS-BfEl1dInwuzIz8Ir5s9b3TFBg0VI1R"
DEVICE_LABEL = "raspberrypi"
VARIABLE_LABEL = "new-variable-2"

# Global Variables
ALARM_DATETIME = None
TEMPO = 1.0
last_alarm_trigger = None

# HTTP
def send_http_to_ubidots(value):
    url = f"http://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}"
    headers = {"X-Auth-Token": UBIDOTS_TOKEN, "Content-Type": "application/json"}
    data = {VARIABLE_LABEL: value}
    
    try:
        response = urequests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"HTTP Sent {value} Degrees Celsius to Ubidots")
        else:
            print(f"HTTP Error {response.status_code}: {response.text}")
        response.close()
        return response.status_code == 200
    except Exception as e:
        print("HTTP Request Failed:", e)
        return False

def test_http_connection():
    print("\nTesting HTTP Connection...")
    if send_http_to_ubidots(25.5):
        print("HTTP Test Successful")
        return True
    else:
        print("HTTP Test Failed")
        return False

# Alarm Config
def get_alarm_time():
    global ALARM_DATETIME, REPEAT_DAILY, TEMPO
    print("Example: 2023,12,25,7,30 for Dec 25 2023 at 7:30 AM")
    
    while True:
        try:
            inp = input("Enter alarm time (year,month,day,hour,minute): ")
            year, month, day, hour, minute = map(int, inp.split(','))
            
            
            
            while True:
                try:
                    TEMPO = float(input("Tempo (0.1-1.0, 1.0=normal): "))
                    if 0.1 <= TEMPO <= 1.0: break
                    print("Please enter 0.1 to 1.0")
                except ValueError:
                    print("Enter a number")
            
            return (year, month, day, hour, minute), TEMPO
            
        except (ValueError, IndexError):
            print("Error: Enter exactly 5 numbers separated by commas")

# Summer Time
def is_summer_time(now):

    year, month = now[0], now[1]
    if 3 < month < 10: return True
    if month == 3 and now[2] >= (31 - (5 * year + 4) // 7 % 7): return True
    if month == 10 and now[2] < (31 - (5 * year + 1) // 7 % 7): return True
    return False

def get_local_time():

    now_utc = utime.localtime()
    offset = 2 if is_summer_time(now_utc) else 1  # CEST or CET
    adjusted = utime.mktime(now_utc) + offset * 3600
    return utime.localtime(adjusted)

# Sensor Functions
def read_temperature():
    adc_value = adc.read_u16()
    voltage = (adc_value / 65535) * 3.3
    
    # MCP9700 formula: Temp (°C) = (Vout - 0.5) / 0.01
    temp = (voltage - 0.5) / 0.01
    
    # Added calibration offset
    calibration_offset = -2.0  # Subtract 2 degree to match reference thermometer
    calibrated_temp = temp + calibration_offset
    
    return round(calibrated_temp, 1)

# Tune Functions
def play_tune(melody, tempo):
   
    for note_info in melody:
        note = note_info[1]
        duration = note_info[2]
        
        if note == 'R':
            buzzer.duty_u16(0)
        else:
            buzzer.freq(NOTES[note])
            buzzer.duty_u16(32768)
        sleep(duration * tempo)
    buzzer.duty_u16(0)

def check_alarm(current_time):

    global last_alarm_trigger
    
    if ALARM_DATETIME is None:
        return False
        
    current_minute = (current_time[3], current_time[4])
    
    if last_alarm_trigger == current_minute:
        return False
        
    if REPEAT_DAILY:
        alarm_triggered = (current_time[3], current_time[4]) == (ALARM_DATETIME[3], ALARM_DATETIME[4])
    else:
        alarm_triggered = current_time[:5] == ALARM_DATETIME[:5]
    
    if alarm_triggered:
        last_alarm_trigger = current_minute
        temp = read_temperature()
        print(f"\nALARM! {current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d}")
        print(f"Time: {current_time[3]:02d}:{current_time[4]:02d} | Temp: {temp} Degrees Celsius.")
        return True
    return False

# WiFi Connection
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(20):
        if wlan.isconnected():
            return
        utime.sleep(1)
    raise RuntimeError("WiFi failed")

# Display Function
def display_clock():
    local_time = get_local_time()
    temp = read_temperature()
    
    oled.fill(0)  # Clear display
    
    
    oled.text(f"{local_time[3]:02d}:{local_time[4]:02d}:{local_time[5]:02d}", -1, 30, 1)  
  
    oled.text(f"{local_time[0]}-{local_time[1]:02d}-{local_time[2]:02d}", -1, 40, 1)  
    
    oled.text(f"Temperature:", -1, 50, 1)  
    oled.text(f"{temp:.1f}", -1, 60, 1)
    oled.text(f"Degrees", -1,70, 1)
    oled.text(f"Celsius", -1, 80, 1)
    
    oled.show()

# Main
def main():
    # Initial display test
    oled.fill(0)
    oled.text("Starting...", -1, 30, 1)
    oled.show()
    
    # Connect to WiFi
    try:
        connect_wifi()
        ntptime.settime()
        print("Time synchronized")
    except Exception as e:
        print("WiFi/NTP failed:", e)
        oled.fill(0)
        oled.text("WiFi Error", -1, 30, 1)
        oled.show()
        return
    
    if not test_http_connection():
        oled.fill(0)
        oled.text("HTTP Failed", -1, 50, 1)
        oled.show()
        return
    
    # Get alarm time
    global ALARM_DATETIME, TEMPO
    ALARM_DATETIME, TEMPO = get_alarm_time()
    
    print("System running...")
    last_sent_minute = -1
    
    while True:
        try:
            local_time = get_local_time()
            current_minute = local_time[4]
            temp = read_temperature()
            
            # Update display
            display_clock()
            
            # Send data to Ubidots once per minute
            if current_minute != last_sent_minute:
                if send_http_to_ubidots(temp):
                    last_sent_minute = current_minute
            
            # Check alarm
            if check_alarm(local_time):
                play_tune(MELODY, TEMPO)
            
            sleep(0.5)
            
        except Exception as e:
            print("Error:", e)
            buzzer.duty_u16(0)
            sleep(5)

main()