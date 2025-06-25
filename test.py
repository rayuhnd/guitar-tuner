from machine import I2C, Pin
import framebuf

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

# Initialize I2C & display
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
oled = SH1107(128, 128, i2c)

# Test display
oled.fill(0)
oled.text("Hello!", 10, 10, 1)
oled.text("SH1107 Working?", 10, 30, 1)
oled.show()