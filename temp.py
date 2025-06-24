from machine import Pin, ADC, PWM # type: ignore
import utime # type: ignore
import network # type: ignore
import ntptime # type: ignore
from notes import NOTES
from melody import MELODY
from utime import sleep # type: ignore

# --- Hardware Setup ---
adc = ADC(Pin(26))          # Temperature sensor (GP26)
buzzer = PWM(Pin(16))       # Passive piezo on GP16 (changed from GP15 to match comment)
buzzer.duty_u16(0)          # Start with buzzer off

# --- WiFi Config ---
WIFI_SSID = "Google Björkgatan"
WIFI_PASSWORD = "wash@xidi"

# --- Alarm Config ---
def get_alarm_time():
    """Get alarm time from user input and return as tuple"""
    print("Example: 2023,12,25,7,30 for Dec 25 2023 at 7:30 AM")
    while True:
        inp = input("Enter alarm time as: year,month,day,hour,minute: ").strip()
        parts = inp.split(',')
        if len(parts) != 5:
            print("Error: Need exactly 5 numbers separated by commas")
            continue
            
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            hour = int(parts[3])
            minute = int(parts[4])
            return (year, month, day, hour, minute)
        except:
            print("Error: All values must be numbers")

ALARM_DATETIME = get_alarm_time()  # Get user input for alarm time
ALARM_DURATION = 10         # Alarm duration in seconds
REPEAT_DAILY = True         # If True, ignores date and repeats daily at specified time

# --- Timezone/DST for Sweden ---
def is_summer_time(now):
    """Returns True if Swedish summer time (CEST) is active"""
    year, month = now[0], now[1]
    if 3 < month < 10:  # April-Sept = always summer time
        return True
    if month == 3 and now[2] >= (31 - (5 * year + 4) // 7 % 7):  # Last Sunday March
        return True
    if month == 10 and now[2] < (31 - (5 * year + 1) // 7 % 7):  # Last Sunday October
        return True
    return False

def get_local_time():
    """Returns Swedish local time (CET/CEST) as (year, month, day, hour, minute, second, ...)"""
    now_utc = utime.localtime()
    offset = 2 if is_summer_time(now_utc) else 1  # CEST (UTC+2) or CET (UTC+1)
    adjusted = utime.mktime(now_utc) + offset * 3600
    return utime.localtime(adjusted)

# --- Temperature Sensor ---
def read_temperature():
    adc_value = adc.read_u16()
    voltage = (adc_value / 65535) * 3.3
    return round((voltage - 0.5) / 0.01, 1)  # MCP9700 formula

# --- Alarm Functions ---
def play_tune(melody=MELODY, tempo=1):
    for note_info in melody:
        # Unpack note information (assuming format: (_, note, duration, _))
        note = note_info[1]
        duration = note_info[2]
        
        if note == 'R':  # Rest
            buzzer.duty_u16(0)
        else:
            buzzer.freq(NOTES[note])
            buzzer.duty_u16(32768)  # 50% duty cycle
        sleep(duration * tempo / 10)
    buzzer.duty_u16(0)  # Ensure buzzer is off after melody

def check_alarm(current_time):
    """Check if current time matches alarm conditions"""
    if ALARM_DATETIME is None:
        return False
        
    if REPEAT_DAILY:
        # Only check hour and minute
        return (current_time[3], current_time[4]) == (ALARM_DATETIME[3], ALARM_DATETIME[4])
    else:
        # Check full date and time
        return current_time[:5] == ALARM_DATETIME[:5]

# --- Main Program ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(20):
        if wlan.isconnected():
            return
        utime.sleep(1)
    raise RuntimeError("WiFi failed")

try:
    # Initialize
    connect_wifi()
    ntptime.settime()  # Sync UTC
    
    # Main loop
    while True:
        # Get local time
        local_time = get_local_time()
        hour, minute = local_time[3], local_time[4]
        day, month, year = local_time[2], local_time[1], local_time[0]
        temp = read_temperature()
        
        # Display
        print(f"Date: {year}-{month:02d}-{day:02d} Time: {hour:02d}:{minute:02d} | Temp: {temp} Degrees Celsius")
        
        # Check alarm
        if check_alarm(local_time):
            play_tune(MELODY)  # Pass the melody to play
            if not REPEAT_DAILY:
                ALARM_DATETIME = None  # Disable after triggering if not repeating
        
        utime.sleep(60 - utime.time() % 60)  # Sync to whole minute

except Exception as e:
    buzzer.duty_u16(0)  # Ensure buzzer is off on error
    print("Error:", e)