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

# ===== WORKING SH1107 DRIVER =====
class SH1107:
    def __init__(self, width=128, height=128, i2c=None, addr=0x3C):
        self.width = width
        self.height = height
        self.pages = height // 8
        self.addr = addr
        self.i2c = i2c
        self.buffer = bytearray(self.pages * width)
        self.framebuf = framebuf.FrameBuffer(self.buffer, width, height, framebuf.MONO_VLSB)
        
        # Initialize display
        self.init_cmds = bytes([
            0xAE, 0x00, 0x10, 0x40, 0x81, 0xCF, 0xA1, 0xC8,
            0xA6, 0xA8, 0x3F, 0xD3, 0x00, 0xD5, 0x80, 0xD9,
            0xF1, 0xDA, 0x12, 0xDB, 0x40, 0x20, 0x00, 0x8D,
            0x14, 0xA4, 0xA6, 0xAF
        ])
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
            self.write_cmd(0xB0 + page)
            self.write_cmd(0x00)
            self.write_cmd(0x10)
            self.write_data(self.buffer[page * self.width:(page + 1) * self.width])

# ===== HARDWARE SETUP =====
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
oled = SH1107(128, 128, i2c)  # Initialize display

adc = ADC(Pin(26))  # Temperature sensor
buzzer = PWM(Pin(18))       
buzzer.duty_u16(0)  # Start with buzzer off

# ===== NETWORK CONFIG =====
WIFI_SSID = "Google Björkgatan"
WIFI_PASSWORD = "wash@xidi"
UBIDOTS_TOKEN = "BBUS-BfEl1dInwuzIz8Ir5s9b3TFBg0VI1R"
DEVICE_LABEL = "raspberrypi"
VARIABLE_LABEL = "new-variable-2"

# ===== GLOBAL VARIABLES =====
ALARM_DATETIME = None
REPEAT_DAILY = False
TEMPO = 1.0
last_alarm_trigger = None

# ===== HTTP FUNCTIONS =====
def send_http_to_ubidots(value):
    url = f"http://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}"
    headers = {"X-Auth-Token": UBIDOTS_TOKEN, "Content-Type": "application/json"}
    data = {VARIABLE_LABEL: value}
    
    try:
        response = urequests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"HTTP Sent {value}°C to Ubidots")
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
        print("✓ HTTP Test Successful")
        return True
    else:
        print("✗ HTTP Test Failed")
        return False

# ===== ALARM CONFIG =====
def get_alarm_time():
    """Get alarm time from user input"""
    global ALARM_DATETIME, REPEAT_DAILY, TEMPO
    print("Example: 2023,12,25,7,30 for Dec 25 2023 at 7:30 AM")
    
    while True:
        try:
            inp = input("Enter alarm time (year,month,day,hour,minute): ")
            year, month, day, hour, minute = map(int, inp.split(','))
            
            REPEAT_DAILY = input("Repeat daily? (y/n): ").lower() == 'y'
            
            while True:
                try:
                    TEMPO = float(input("Tempo (0.1-1.0, 1.0=normal): "))
                    if 0.1 <= TEMPO <= 1.0: break
                    print("Please enter 0.1 to 1.0")
                except ValueError:
                    print("Enter a number")
            
            return (year, month, day, hour, minute), REPEAT_DAILY, TEMPO
            
        except (ValueError, IndexError):
            print("Error: Enter exactly 5 numbers separated by commas")

# ===== TIME FUNCTIONS =====
def is_summer_time(now):
    """Check if DST is active (Sweden)"""
    year, month = now[0], now[1]
    if 3 < month < 10: return True
    if month == 3 and now[2] >= (31 - (5 * year + 4) // 7 % 7): return True
    if month == 10 and now[2] < (31 - (5 * year + 1) // 7 % 7): return True
    return False

def get_local_time():
    """Get local time with DST adjustment"""
    now_utc = utime.localtime()
    offset = 2 if is_summer_time(now_utc) else 1  # CEST or CET
    adjusted = utime.mktime(now_utc) + offset * 3600
    return utime.localtime(adjusted)

# ===== SENSOR FUNCTIONS =====
def read_temperature():
    """Read temperature from ADC"""
    adc_value = adc.read_u16()
    voltage = (adc_value / 65535) * 3.3
    return round((voltage - 0.5) / 0.01, 1)

# ===== ALARM FUNCTIONS =====
def play_tune(melody, tempo):
    """Play melody with adjustable tempo"""
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
    """Check if alarm should trigger"""
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
        print(f"Time: {current_time[3]:02d}:{current_time[4]:02d} | Temp: {temp}°C")
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

# ===== DISPLAY FUNCTION =====
def display_clock():
    """Update OLED display with time, date, temp, and alarm status"""
    local_time = get_local_time()
    temp = read_temperature()
    
    oled.fill(0)
    
    # Time (HH:MM:SS)
    oled.text(f"{local_time[3]:02d}:{local_time[4]:02d}:{local_time[5]:02d}", 10, 30, 1)
    
    # Date (YYYY-MM-DD)
    oled.text(f"{local_time[0]}-{local_time[1]:02d}-{local_time[2]:02d}", 10, 50, 1)
    
    # Temperature
    oled.text(f"Temp: {temp:.1f}C", 10, 70, 1)
    
    # Alarm status
    if ALARM_DATETIME:
        alarm_str = f"Alarm: {ALARM_DATETIME[3]:02d}:{ALARM_DATETIME[4]:02d}"
        oled.text(alarm_str, 10, 90, 1)
        if REPEAT_DAILY:
            oled.text("(Daily)", 80, 90, 1)
    
    oled.show()

# ===== MAIN PROGRAM =====
def main():
    # Initial display test
    oled.fill(0)
    oled.text("Starting...", 10, 10, 1)
    oled.show()
    
    # Connect to WiFi
    try:
        connect_wifi()
        ntptime.settime()
        print("Time synchronized")
    except Exception as e:
        print("WiFi/NTP failed:", e)
        oled.fill(0)
        oled.text("WiFi Error", 10, 30, 1)
        oled.show()
        return
    
    if not test_http_connection():
        oled.fill(0)
        oled.text("HTTP Failed", 10, 50, 1)
        oled.show()
        return
    
    # Get alarm time
    global ALARM_DATETIME, REPEAT_DAILY, TEMPO
    ALARM_DATETIME, REPEAT_DAILY, TEMPO = get_alarm_time()
    
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
                if not REPEAT_DAILY:
                    ALARM_DATETIME = None  # Disable one-time alarm
            
            sleep(0.5)
            
        except Exception as e:
            print("Error:", e)
            buzzer.duty_u16(0)
            sleep(5)

# Start program
if __name__ == "__main__":
    main()