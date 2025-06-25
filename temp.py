from machine import Pin, ADC, PWM, I2C
import utime
import network
import ntptime
from notes import NOTES
from melody import MELODY
from utime import sleep
import ujson
import urequests
import framebuf

# SH1107 display commands
_SET_CONTRAST        = 0x81
_SET_ENTIRE_ON       = 0xA4
_SET_NORM_INV        = 0xA6
_SET_DISP            = 0xAE
_SET_MEM_ADDR        = 0x20
_SET_COL_ADDR        = 0x21
_SET_PAGE_ADDR       = 0x22
_SET_DISP_START_LINE = 0x40
_SET_SEG_REMAP       = 0xA0
_SET_MUX_RATIO       = 0xA8
_SET_COM_OUT_DIR     = 0xC0
_SET_DISP_OFFSET     = 0xD3
_SET_COM_PIN_CFG     = 0xDA
_SET_DISP_CLK_DIV    = 0xD5
_SET_PRECHARGE       = 0xD9
_SET_VCOM_DESEL      = 0xDB
_SET_CHARGE_PUMP     = 0x8D

class SH1107(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        self.i2c = i2c
        self.addr = addr
        self.init_display()
    
    def init_display(self):
        for cmd in (
            _SET_DISP | 0x00,  # Display off
            _SET_MEM_ADDR, 0x00,  # Horizontal addressing mode
            _SET_DISP_START_LINE | 0x00,
            _SET_SEG_REMAP | 0x01,  # Column 127 mapped to SEG0
            _SET_MUX_RATIO, self.height - 1,
            _SET_COM_OUT_DIR | 0x08,  # Scan from COM[N-1] to COM0
            _SET_DISP_OFFSET, 0x00,
            _SET_COM_PIN_CFG, 0x12 if self.height == 128 else 0x02,
            _SET_DISP_CLK_DIV, 0x80,
            _SET_PRECHARGE, 0x22 if self.external_vcc else 0xF1,
            _SET_VCOM_DESEL, 0x30,  # 0.83*Vcc
            _SET_CONTRAST, 0xFF,  # Maximum contrast
            _SET_ENTIRE_ON,  # Output follows RAM contents
            _SET_NORM_INV,  # Non-inverted display
            _SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14,
            _SET_DISP | 0x01):  # Display on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()
    
    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytearray([0x00, cmd]))
    
    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40' + buf)
    
    def show(self):
        for page in range(self.pages):
            self.write_cmd(_SET_PAGE_ADDR)
            self.write_cmd(page)
            self.write_cmd(_SET_COL_ADDR)
            self.write_cmd(0)
            self.write_cmd(self.width - 1)
            self.write_data(self.buffer[page * self.width:(page + 1) * self.width])
    
    def set_contrast(self, contrast):
        self.write_cmd(_SET_CONTRAST)
        self.write_cmd(contrast)

# Initialize I2C with proper pins
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
oled = SH1107(128, 128, i2c)
oled.set_contrast(255)  # Use the new set_contrast method

# Hardware Setup
adc = ADC(Pin(26))  # Temperature sensor (GP26)
buzzer = PWM(Pin(18))       
buzzer.duty_u16(0)  # Start with buzzer off

# WiFi Config
WIFI_SSID = "Google Björkgatan"
WIFI_PASSWORD = "wash@xidi"

# Ubidots Config
UBIDOTS_TOKEN = "BBUS-BfEl1dInwuzIz8Ir5s9b3TFBg0VI1R"
DEVICE_LABEL = "raspberrypi"
VARIABLE_LABEL = "new-variable-2"

# Global variables
ALARM_DATETIME = None
REPEAT_DAILY = False
TEMPO = 1.0
last_alarm_trigger = None

# HTTP Functions
def send_http_to_ubidots(value):
    url = "http://industrial.api.ubidots.com/api/v1.6/devices/{}".format(DEVICE_LABEL)
    headers = {
        "X-Auth-Token": UBIDOTS_TOKEN,
        "Content-Type": "application/json"
    }
    data = {VARIABLE_LABEL: value}
    
    try:
        response = urequests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print("HTTP Sent {} Degrees Celsius to Ubidots".format(value))
        else:
            print("HTTP Error {}: {}".format(response.status_code, response.text))
        response.close()
        return response.status_code == 200
    except Exception as e:
        print("! HTTP Request Failed:", e)
        return False

def test_http_connection():
    print("\n=== Testing HTTP Connection ===")
    test_value = 25.5
    print("Attempting to send test value:", test_value)
    if send_http_to_ubidots(test_value):
        print("✓ HTTP Test Successful")
        return True
    else:
        print("! HTTP Test Failed")
        return False

# Alarm Config
def get_alarm_time():
    """Get alarm time from user input and return as tuple"""
    global ALARM_DATETIME, REPEAT_DAILY, TEMPO
    print("Example: 2023,12,25,7,30 for Dec 25 2023 at 7:30 AM")
    while True:
        try:
            # Get alarm time
            inp = input("Enter alarm time as: year,month,day,hour,minute: ")
            parts = inp.split(",")
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            hour = int(parts[3])
            minute = int(parts[4])
            
            # Get repeat preference
            while True:
                repeat_input = input("Repeat daily? (True/False): ").strip().lower()
                if repeat_input in ['true', 'false']:
                    REPEAT_DAILY = repeat_input == 'true'
                    break
                print("Please enter exactly 'True' or 'False'")
            
            # Get tempo
            while True:
                try:
                    TEMPO = float(input("Enter tempo (0.1-1.0 where 1.0 is normal speed): "))
                    if 0.1 <= TEMPO <= 1.0:
                        break
                    print("Please enter a value between 0.1 and 1.0")
                except ValueError:
                    print("Please enter a number")
            
            return (year, month, day, hour, minute), REPEAT_DAILY, TEMPO
            
        except (ValueError, IndexError):
            print("Error: Please enter exactly 5 numbers separated by commas")

# Get alarm settings
ALARM_DATETIME, REPEAT_DAILY, TEMPO = get_alarm_time()

# Timezone/DST for Sweden
def is_summer_time(now):
    year, month = now[0], now[1]
    if 3 < month < 10:
        return True
    if month == 3 and now[2] >= (31 - (5 * year + 4) // 7 % 7):
        return True
    if month == 10 and now[2] < (31 - (5 * year + 1) // 7 % 7):
        return True
    return False

def get_local_time():
    now_utc = utime.localtime()
    offset = 2 if is_summer_time(now_utc) else 1
    adjusted = utime.mktime(now_utc) + offset * 3600
    return utime.localtime(adjusted)

# Temperature Sensor
def read_temperature():
    adc_value = adc.read_u16()
    voltage = (adc_value / 65535) * 3.3
    return round((voltage - 0.5) / 0.01, 1)

# Alarm Functions
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
    global last_alarm_trigger, ALARM_DATETIME
    
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
        print(f"\nALARM! Date: {current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d}")
        print(f"Time: {current_time[3]:02d}:{current_time[4]:02d} | Temperature indoor is: {temp} Degrees Celsius.")
    return alarm_triggered

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
    
    oled.fill(0)
    
    # Time (HH:MM:SS)
    time_str = "{:02d}:{:02d}:{:02d}".format(local_time[3], local_time[4], local_time[5])
    oled.text(time_str, 10, 30, 1)
    
    # Date (YYYY-MM-DD)
    date_str = "{:04d}-{:02d}-{:02d}".format(local_time[0], local_time[1], local_time[2])
    oled.text(date_str, 10, 50, 1)
    
    # Temperature
    temp_str = "Temp: {:.1f}C".format(temp)
    oled.text(temp_str, 10, 70, 1)
    
    # Alarm status if set
    if ALARM_DATETIME:
        alarm_str = "Alarm: {:02d}:{:02d}".format(ALARM_DATETIME[3], ALARM_DATETIME[4])
        oled.text(alarm_str, 10, 90, 1)
        if REPEAT_DAILY:
            oled.text("(Daily)", 80, 90, 1)
    
    oled.show()

# Main Program
def main():
    connect_wifi()
    ntptime.settime()
    
    if not test_http_connection():
        print("HTTP test failed")
        oled.fill(0)
        oled.text("HTTP Failed", 10, 30, 1)
        oled.show()
        return
    
    print("System starting...")
    last_sent_minute = -1
    
    while True:
        try:
            local_time = get_local_time()
            current_minute = local_time[4]
            temp = read_temperature()
            
            # Update display every second
            display_clock()
            
            # Original HTTP logic
            if current_minute != last_sent_minute:
                if send_http_to_ubidots(temp):
                    last_sent_minute = current_minute
            
            # Original alarm logic
            if check_alarm(local_time):
                play_tune(MELODY, TEMPO)
                if not REPEAT_DAILY:
                    ALARM_DATETIME = None
            
            sleep(0.5)  # Faster update for smoother clock
            
        except Exception as e:
            print("Error:", e)
            buzzer.duty_u16(0)
            sleep(5)

main()