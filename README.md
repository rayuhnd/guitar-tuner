# Guitar Tuner

Ryan Shi Ding / rs223re

In this project, I’ve created an embedded system that listens to a vibrating guitar string through a piezo knock sensor, processes the signal to determine its frequency, and provides visual feedback through LEDs to help the user tune their instrument. The system uses a Raspberry Pi Pico WH to collect the signal, estimate the string frequency, and display tuning accuracy via RGB LEDs. The idea is to give real-time tuning feedback without requiring a display or phone app.

This project takes roughly 4–8 hours depending on your experience with signal processing and microcontrollers.

## Objective
As a guitarist, I’ve often found it inconvenient to grab a separate tuner or phone app when I just want to quickly tune up before playing. This project aims to create a compact, physical tuner that listens to a plucked string through vibrations captured by a piezo knock sensor. Using the Raspberry Pi Pico WH, I perform frequency analysis and give instant feedback through colored LEDs to indicate whether the string is flat, sharp, or in tune.

The system is standalone and portable. While this prototype doesn’t yet include IoT features, such as logging or wireless sync, they could easily be added in future iterations.

Below is a table of the main components used in the project.

| Component            | Link                                                                        | Price   |
| -------------------- | --------------------------------------------------------------------------- | ------- |
| Raspberry Pi Pico WH | [Electrokit](https://www.electrokit.com/raspberry-pi-pico-wh)               | 109 SEK |
| DHT11                | [Electrokit](https://www.electrokit.com/temp/fuktsensor-dht11)              | 39 SEK  |
| Piezo                | [Electrokit](https://www.electrokit.com/piezoelement-20mm-med-sladd)              | 22 SEK  |
| RGB LED              | [Electrokit](https://www.electrokit.com/led-rgb-5mm-adresserbar-ws2812d-f5) | 5 SEK   |

In addition, you need a breadboard, resistors, jumper wires and a USB-A to micro USB cable. These can all be bought at Electrokit. An example of what resistors and wires needed and how they can be connected will be provided later on in [Putting Everything Together](#putting-everything-together).

### Raspberry Pi Pico WH

The Raspberry Pi Pico WH is the microcontroller used in the project. It has a micro-USB port that is used to give it power and to program it by uploading code. There are ground, power and GPIO pins so that electrical components can be connected and controlled by the microcontroller. This microcontroller can also connect to WiFi which makes it able to send and recieve messages wirelessly.

<img src="https://github.com/gnowin/iot-project/assets/100692493/f471fdd4-94a1-4c5e-bd69-ecc444c994b7" alt="pico" style="width:50%;"/>

### DHT11

A sensor that measures both humidity and temperature.

<img src="https://github.com/gnowin/iot-project/assets/100692493/8af396f4-aee0-4e85-ad96-587265f504fc" alt="dht11" style="width:50%;"/>

### Piezo

A piezo can detect vibrations and make noises.

<img src="https://github.com/gnowin/iot-project/assets/100692493/4f787bc6-96eb-4d2e-aee0-624b47ec20e8" alt="piezo" style="width:50%;"/>

### RGB LED

An LED that can display a multitude of colors. It has one pin for power, and three pins that correspond to the intensity of the red, green and blue color channels to light up in different colors.

<img src="https://github.com/gnowin/iot-project/assets/100692493/275643b6-6dea-4d1e-8785-101b64a72f7f" alt="rgbled" style="width:50%;"/>

## Computer setup

Here I will explain my computer setup for this project. The tools I used are:

* Visual Studio Code
* Node.js
* Pymakr extension
* Micropython firmware (for microcontroller)

### Visual Studio Code

The IDE I used for this project is Visual Studio Code, which can be downloaded [here](https://code.visualstudio.com/).

### Pymakr

To interact with the microcontroller I used Pymakr. It is a Visual Studio Code extension you can download by searching on it in the extensions tab in the application. A guide to getting started can be read [here](https://github.com/sg-wireless/pymakr-vsc/blob/HEAD/GET_STARTED.md).

### Node.js

Pymakr needs Node.js to work, you can download it from their [website](https://nodejs.org/en).

### Micropython firmware

To use Raspberry Pi Pico WH and upload micropython files from your computer, you need to update its firmware. The micropython firmware can be downloaded from [this](https://micropython.org/download/RPI_PICO_W/) website. Follow the installation instructions.

## Putting everything together

<img src="https://github.com/gnowin/iot-project/assets/100692493/c6f84446-b17f-45d3-b00c-db5fa1ac49fd" alt="wiring_diagram" style="width:50%;"/>

This is a simplified view of the wiring, showing what types of resistors are used and which pins the different components are connected to. This image is created in WokWi, and as there was no DHT11 component present in the application, a DHT22 sensor is shown instead. However, the purpose is to show how you could wire it and the amount of pins are and same for both sensors so the wiring is correct anyways.

## Platform

I had an old laptop laying around that I wanted to turn into a server, so early on I made the decision to self-host the server side of the project. I also wanted to try out Docker for the first time.

I installed Ubuntu Server on the laptop, but as I set this up with Docker it should work on most operating systems. Before deploying it on my Ubuntu Server I worked on it on my Windows 10 computer.

The server's stack consists of the following:

* Eclipse Mosquitto: MQTT Broker.
* Telegraf: Gathers data from MQTT Broker and sends it to database.
* InfluxDB: Time-series database.
* Grafana: Connects to the InfluxDB database. Grafana provides a multitude of visualization options to display data, e.g. different graphs.

There are configuration files in the repository that can be changed for anyone's liking. However, only the "CHANGEME" rows in the ".env" have to be changed to get the server side working. Read the additional "README" files for further instructions.

## The code

In the boot file, there is code that attempts to connect to a WiFi network through the [network](https://docs.micropython.org/en/latest/library/network.html) library, and then tests the connection by using the [socket](https://docs.micropython.org/en/latest/library/socket.html) library. The WiFi network credentials are stored in a secrets file. These libraries are built-in modules within micropython. I will not go through the details of these functions, but they are called through two different error exception handlings.

```python
# WiFi Connection
try:
    ip = connect()
except KeyboardInterrupt:
    print("Keyboard interrupt")

# HTTP request
try:
    http_get()
except (Exception, KeyboardInterrupt) as err:
    print("No Internet", err)
```

The majority of the code is in the main file. It consists of some initializations and a loop for the microcontrollers logic. To connect and send data to the MQTT Broker, [umqtt_simple](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py) library is used. A MQTT client object is created

```python
client = MQTTClient(ClientID, secrets.MQTT_SERVER, 1883)
```

and then later attempts to connect to the broker. If it doesn't succeed in connecting, it tries to reconnect until it does.

```python
#Try to connect, reconnect
try:
    connect(client)
except OSError as e:
    reconnect(client)
```

Also before the main loop, objects that define what pin and how to interact with the different components on the board are initiated.

```python
# On-board LED
led = Pin("LED", Pin.OUT)

# DHT11 sensor
sensor = dht.DHT11(Pin(16))

# Piezo
buzzer = PWM(Pin(17))

# RGB LED (only red and blue)
ledR = PWM(Pin(11), freq=300_00, duty_u16=0)
ledB = PWM(Pin(14), freq=300_00, duty_u16=0)
```

If the MQTT connection is successful, the main loop is initiated and will never leave the loop unless the microcontroller is restarted. The main loop does the following:

1. Reads temperature and humidity from sensor.
2. Compares last temperature with current, and makes piezo do a sound if changed. Lower frequency for a lowered value, higher frequency for higher value.
3. Updates RGB LED color. It is more blue on lower temperatures and more red on higher.
4. Sends data in a json format and blinks the onboard LED.
5. Sleeps/waits for 60 seconds to continue with the next loop.

## Transmitting the data / connectivity

As explained in the previous section, a wireless connection is established on the microcontroller with a WiFi protocol with the built-in [network](https://docs.micropython.org/en/latest/library/network.html) library.

```python
def connect():
    wlan = network.WLAN(network.STA_IF)         # Put modem on Station mode
    if not wlan.isconnected():                  # Check if already connected
        print('connecting to network...')
        wlan.active(True)                       # Activate network interface

        # set power mode to get WiFi power-saving off (if needed)
        wlan.config(pm = 0xa11140)
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)  # Your WiFi Credential
        print('Waiting for connection...', end='')
        
        # Check if it is connected otherwise wait
        while not wlan.isconnected() and wlan.status() >= 0:
            print('.', end='')
            sleep(1)
            
    # Print the IP assigned by router
    ip = wlan.ifconfig()[0]
    print('\nConnected on {}'.format(ip))
    return ip
```

Through the [json](https://docs.micropython.org/en/latest/library/json.html) library, a dictionary of the data is converted to json and then sent with the publish function with help from the [umqtt_simple](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py) client object. The library uses the MQTT transport protocol. The data is sent every minute.

```python
# Prepare message data
msg = {
    "temperature": temp,
    "humidity": hum
}

# Send data
send_data(client, led, msg)
```

```python
def send_data(c, led, msg):
    print('send message %s on topic %s' % (msg, topic))
    try: 
        c.publish(topic, json.dumps(msg), qos=0)
    except OSError as e:
        print(e)
    led.on()
    time.sleep(0.2)
    led.off()
    time.sleep(0.8)
```

## Presenting the data

Using Grafana I have built a dashboard to visualize my data. The dashboard consists of one graph and one gauge each for both temperature and humidity. The graph shows the data values over time, and the gauge shows the current value (the value sent last).

Here is the view on my computer:

<img src="https://github.com/gnowin/iot-project/assets/100692493/c6a61c10-213c-4201-b367-4bcdf54784b3" alt="grafanapc" style="width:100%;"/>

And here is the view on mobile. The left picture is the dashboard when fully scrolled up, and the right one is when you scroll down past the gauges.

<img src="https://github.com/gnowin/iot-project/assets/100692493/7e5d7b7c-5ef8-43d7-af50-cde740674a59" alt="grafanamobile" style="width:49%;"/>

<img src="https://github.com/gnowin/iot-project/assets/100692493/4f1c7405-3e84-447b-b7ab-244811bb9f92" alt="grafanamobile2" style="width:49%;"/>

By default and in my testing, the data is just preserved for four days, but this can be changed in the configurations.

## Finalizing the design

Here is the final result of my project:

<img src="https://github.com/gnowin/iot-project/assets/100692493/7fb8958b-f80d-49b3-96c1-c5bd53c4067d" alt="finalresult" style="width:100%;"/>

The result is simpler than what I first imagined I would do. I had several ideas that included an LCD screen I had around to make an interactive system, but I realized late into the project that the contrast of the screen was not working properly. I also wanted to explore Node-RED to control the microcontroller wirelessly, but that will have to be a future project. But overall I am happy that I managed to get a plan B working and I still learned a lot throughout this course.