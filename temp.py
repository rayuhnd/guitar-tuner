from machine import Pin, ADC
import utime

# Initialize ADC on GP26 (ADC0)
adc = ADC(Pin(26))

# MCP9700 characteristics
V0 = 0.5  # Voltage at 0°C (500mV)
TC = 0.01  # Temperature coefficient (10mV/°C)

def read_temperature():
    # Read ADC value (0-65535 for 0-3.3V)
    adc_value = adc.read_u16()
    
    # Convert to voltage (Pico ADC is 3.3V range)
    voltage = (adc_value / 65535) * 3.3
    
    # Calculate temperature (MCP9700 formula)
    temperature = (voltage - V0) / TC
    
    return round(temperature, 1)

while True:
    # Get current time
    current_time = utime.localtime()
    year, month, day, hour, minute, second, weekday, yearday = current_time
    
    print("Date: {}-{:02d}-{:02d} Time: {:02d}:{:02d}:{:02d}".format(
        year, month, day, hour, minute, second))
    
    try:
        temp = read_temperature()
        print("Temperature: {:.1f} Degrees Celsius.".format(temp))
    
    except Exception as e:
        print("Error reading sensor:", e)
    
    print("\n")
    utime.sleep(60)  # Update every 2 seconds