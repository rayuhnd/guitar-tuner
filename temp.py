from machine import Pin, ADC, PWM
import utime
import network
import ntptime

# --- Hardware Setup ---
adc = ADC(Pin(26))          # Temperature sensor (GP26)
buzzer = PWM(Pin(16))       # Passive piezo on GP15
buzzer.duty_u16(0)          # Start with buzzer off

# --- WiFi Config ---
WIFI_SSID = "Google Björkgatan"
WIFI_PASSWORD = "wash@xidi"

# --- Alarm Config ---
# Set your desired alarm time and date (year, month, day, hour, minute)
# Set to None to disable date check and only use time
ALARM_DATETIME = (2025, 6, 24, 12, 12)  
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
def trigger_alarm():
    print("ALARM! Wake up!")
    for _ in range(ALARM_DURATION * 2):
        buzzer.duty_u16(32767)  # 50% duty cycle
        buzzer.freq(1000)       # 1kHz tone
        utime.sleep_ms(250)
        buzzer.duty_u16(0)      # Off
        utime.sleep_ms(250)

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
            trigger_alarm()
            if not REPEAT_DAILY:
                ALARM_DATETIME = None  # Disable after triggering if not repeating
        
        utime.sleep(60 - utime.time() % 60)  # Sync to whole minute

except Exception as e:
    print("Error:", e)
    buzzer.duty_u16(0)  # Ensure buzzer turns off on crash