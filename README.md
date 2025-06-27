# Temp-Larm  
Ryan Shi Ding / rs223re  

In this project, I've created an embedded temperature monitoring system with alarm functionality. The system uses a Raspberry Pi Pico WH to continuously measure temperature through an MCP9700 sensor, display the readings on an OLED screen, and trigger a buzzer alarm at user-set times. The compact design provides both visual and audible alerts, making it ideal for temperature-sensitive environments.

This project takes roughly 4-8 hours depending on your experience with microcontrollers and embedded systems. The total component cost is approximately 210.50 SEK (excluding common prototyping components).

# Objective  
As someone who needs to monitor temperature in various settings, I wanted a simple, standalone device that could alert me when specific temperature thresholds are reached or at certain times. This project creates a portable temperature monitor with configurable alarms that doesn't require internet connectivity or a smartphone app.

The system is self-contained and battery-friendly. While this prototype focuses on local functionality, IoT features like remote monitoring could easily be added in future versions. Key features include:
- Accurate temperature monitoring (±2°C after calibration)
- Visual display of current time and temperature
- Configurable alarm times 
- Audible alarm notification
- Optional WiFi connectivity for data logging

Below is a table of the main components used in the project:

| Component            | Link                                                                        | Price   |
| -------------------- | --------------------------------------------------------------------------- | ------- |
| Raspberry Pi Pico WH | [Electrokit](https://www.electrokit.com/raspberry-pi-pico-wh)               | 109 SEK |
| MCP9700 TO-92        | [Electrokit](https://www.electrokit.com/mcp9700-to-92-temperaturgivare)     | 10.50 SEK |
| Piezo Passive        | [Electrokit](https://www.electrokit.com/en/piezohogtalare-passiv)           | 29 SEK |
| OLED Screen 128x128  | [AliExpress](https://www.aliexpress.com/item/4000049991220.html)            | 62 SEK |

In addition, you'll need a breadboard, resistors, jumper wires and a USB-A to micro USB cable. These can all be bought at Electrokit. The wiring configuration will be shown in the Putting Everything Together section.

### Raspberry Pi Pico WH  
The Raspberry Pi Pico WH is the microcontroller used in the project. It has a micro-USB port that is used to give it power and to program it by uploading code. There are ground, power and GPIO pins so that electrical components can be connected and controlled by the microcontroller. This microcontroller can also connect to WiFi which makes it able to send and recieve messages wirelessly.

Key specifications:
- RP2040 dual-core ARM Cortex M0+ processor
- 264KB SRAM
- 2MB flash memory
- 26 multifunction GPIO pins
- Built-in temperature sensor
- 12-bit ADC

<img src="https://github.com/gnowin/iot-project/assets/100692493/f471fdd4-94a1-4c5e-bd69-ecc444c994b7" alt="pico" style="width:50%;"/>

### MCP9700 TO-92  
A sensor that measures temperature.

Technical details:
- Operating voltage: 3.1V to 5.5V
- Temperature range: -40°C to +125°C
- Accuracy: ±2°C (0°C to +70°C)
- Linear output: 10mV/°C
- Low power consumption: 6μA (typical)

<img src="https://github.com/rayuhnd/temp-alarm/blob/main/tempgivare.jpg?raw=true" alt="dht11" style="width:50%;"/>

### Piezo Passive  
A piezo can detect vibrations and make noises.

Characteristics:
- Operating voltage: 3-20V
- Resonant frequency: 2.3kHz ±300Hz
- Sound output: ≥85dB
- Compact size: 12mm diameter

<img src="https://raw.githubusercontent.com/rayuhnd/temp-alarm/refs/heads/main/passive%20piezo.webp" alt="piezo" style="width:50%;"/>

### OLED Screen 128x128  
An LED that can display a multitude of colors. It has one pin for power, and three pins that correspond to the intensity of the red, green and blue color channels to light up in different colors.

Display specifications:
- Resolution: 128x128 pixels
- Interface: I2C
- Viewing angle: >160°
- Contrast ratio: 10,000:1
- Power consumption: 0.08W (typical)

<img src="https://raw.githubusercontent.com/rayuhnd/temp-alarm/refs/heads/main/oled.webp" alt="rgbled" style="width:50%;"/>

# Computer setup  
Here I will explain my computer setup for this project. The tools I used are:

- Visual Studio Code  
- Node.js  
- Pymakr extension  
- Micropython firmware (for microcontroller)  

### Visual Studio Code  
The IDE I used for this project is Visual Studio Code, which can be downloaded [here](https://code.visualstudio.com/). Recommended extensions:
- Python (for syntax highlighting)
- Pylance (for code analysis)
- MicroPython (for device support)

### Pymakr  
To interact with the microcontroller I used Pymakr. It is a Visual Studio Code extension you can download by searching on it in the extensions tab in the application. A guide to getting started can be read [here](https://docs.pycom.io/pymakr/installation/vscode/).

Key features:
- Serial terminal
- File transfer
- Code synchronization
- Device management

### Node.js  
Pymakr needs Node.js to work, you can download it from their [website](https://nodejs.org/). Recommended version:
- LTS (Long Term Support) version
- Includes npm package manager

### Micropython firmware  
To use Raspberry Pi Pico WH and upload micropython files from your computer, you need to update its firmware. The micropython firmware can be downloaded from this [website](https://micropython.org/download/rp2-pico/). Follow the installation instructions.

Installation steps:
1. Download UF2 file
2. Hold BOOTSEL button while connecting Pico to USB
3. Drag UF2 file to RPI-RP2 drive
4. Device will reboot automatically

# Putting everything together  
<img src="https://github.com/rayuhnd/temp-alarm/blob/main/wokwi.jpg?raw=true" alt="wiring_diagram" style="width:50%;"/>

This wiring diagram shows how to connect all components to the Raspberry Pi Pico WH. Note that the MCP9700 connects to an analog input pin (3V3(OUT)), while the OLED uses I2C communication.

Complete wiring guide:
1. Connect Pico 3V3(OUT) to breadboard power rail
2. Connect Pico GND to breadboard ground rail
3. MCP9700:
   - VDD to 3V3
   - GND to GND
   - VOUT to GP26 (ADC0)
4. OLED:
   - GND to GND
   - VCC to 3V3
   - SCL to GP17
   - SDA to GP16
5. Piezo buzzer:
   - Positive to GP18
   - Negative to GND

### The Code  
The system uses a simple state machine to manage temperature reading, display updates, and alarm checking. Here are the key components:

### Temperature Reading  
The code reads the analog voltage from the sensor and converts it to temperature using the MCP9700's characteristic equation, with added calibration:

```python
def read_temperature():
    adc_value = adc.read_u16()
    voltage = (adc_value / 65535) * 3.3
    return round((voltage - 0.5) / 0.01, 1)
```

### Alarm Settings  
User-friendly input for setting alarms with validation:

```python
get_alarm_time():
    """Get alarm time from user input"""
    global ALARM_DATETIME, TEMPO
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
```

### Main Loop  
The core system loop handles all functions with error recovery:

```python
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
```

# How It Works  

1. Continuously measures temperature every second using the MCP9700 sensor
2. Displays current temperature and time on OLED with clear formatting
3. Allows setting alarms through serial interface with validation
4. Triggers buzzer when alarm time matches current time
5. Automatically clears alarm after triggering 
6. Optional WiFi connectivity for NTP time sync and data logging

System states:
- Initialization: Sets up hardware and connections
- Configuration: Gets alarm settings from user
- Monitoring: Continuously checks temperature and time
- Alert: Activates when alarm conditions are met
- Error recovery: Handles connection issues gracefully

# Future Improvements  

1. Implement buttons for physical interface
   - Set/clear alarms without serial connection
   - Adjust settings directly on device

2. Add snooze functionality
   - Temporarily silence alarm
   - Automatic re-trigger after delay

3. Add WiFi connectivity for remote monitoring
   - Web interface for configuration
   - Push notifications
   - Historical data logging

4. Battery power optimization
   - Low-power sleep modes
   - Display dimming
   - Motion activation

5. Implement temperature threshold alerts
   - High/low temperature triggers
   - Rate-of-change detection
   - Custom alert sounds

6. Enhanced display features
   - Temperature graphs
   - Multiple alarm indicators
   - System status icons

# Final Design  

Here is the completed temperature alarm system:

<img src="https://github.com/rayuhnd/temp-alarm/blob/main/final%20design.jpeg?raw=true" alt="final_design" style="width:100%;"/>

While simple, this project effectively demonstrates core embedded systems concepts and could be expanded in numerous ways. The clean form factor makes it suitable for various monitoring applications (Note that the OLED screen shown in the image above is rendering - not broken).

Key advantages:
- Standalone operation
- Low power consumption
- Flexible alarm configuration
- Clear visual feedback
- Audible alerts
- Expandable architecture

Potential applications:
- Laboratory equipment monitoring
- Food storage safety
- Greenhouse management
- Home automation
- Industrial process control
