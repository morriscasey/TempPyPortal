import time
import board
import microcontroller
import displayio
import busio
from analogio import AnalogIn
import neopixel
import adafruit_adt7410
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_pyportal import PyPortal
import adafruit_requests as requests
from pyportal import PortalDisplay


# ------------- Constants ------------- #
# Hex Colors
WHITE = 0xFFFFFF
RED = 0xFF0000
YELLOW = 0xFFFF00
GREEN = 0x00FF00
BLUE = 0x0000FF
PURPLE = 0xFF00FF
BLACK = 0x000000

# Default Label styling
TABS_X = 0
TABS_Y = 15


# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.weatherapi.com/v1/current.json?key=" + secrets['api_key'] + "&q=98002&aqi=no"


# ------------- Functions ------------- #
# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    try:
        board.DISPLAY.auto_brightness = False
    except AttributeError:
        pass
    board.DISPLAY.brightness = val


# Helper for cycling through a number set of 1 to x.
def numberUP(num, max_val):
    num += 1
    if num <= max_val:
        return num
    else:
        return 1


# Set visibility of layer
def layerVisibility(state, layer, target):
    try:
        if state == "show":
            time.sleep(0.1)
            layer.append(target)
        elif state == "hide":
            layer.remove(target)
    except ValueError:
        pass

# return a reformatted string with word wrapping using PyPortal.wrap_nicely
def text_box(target, top, string, max_chars):
    text = pyportal.wrap_nicely(string, max_chars)
    new_text = ""
    test = ""

    for w in text:
        new_text += "\n" + w
        test += "M\n"

    text_height = Label(font, text="M", color=GREEN)
    text_height.text = test  # Odd things happen without this
    glyph_box = text_height.bounding_box
    target.text = ""  # Odd things happen without this
    target.y = int(glyph_box[3] / 2) + top
    target.text = new_text


def get_Temperature(source):
    if source:  # Only if we have the temperature sensor
        celsius = source.temperature

    return (celsius * 1.8) + 32


# ------------- Inputs and Outputs Setup ------------- #
light_sensor = AnalogIn(board.LIGHT)
try:
    # attempt to init. the temperature sensor
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
    adt.high_resolution = True
except ValueError:
    # Did not find ADT7410. Probably running on Titano or Pynt
    adt = None

# ------------- Screen Setup ------------- #
pyportal = PyPortal()
pyportal.set_background(BLACK)  # Display an image until the loop starts
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1)


# Touchscreen setup  [ Rotate 0 ]
display = board.DISPLAY
display.rotation = 0


screen_width = 320
screen_height = 240
set_backlight(0.1)

ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(screen_width, screen_height))

# ------------- Display Groups ------------- #
splash = displayio.Group()  # The Main Display Group
view3 = displayio.Group()  # Group for View 3 objects

# ---------- Text Boxes ------------- #
# Set the font and preload letters
font = bitmap_font.load_font("/fonts/PatuaOne-Regular-26.pcf")
font.load_glyphs(b"abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()")

# Text Label Objects
def TemperatureDisplay(view, x, y):
    new_label = Label(font, text="Loading..", color=GREEN)
    new_label.x = x
    new_label.y = y
    view.append(new_label)

    new_data = Label(font, text="Loading..", color=GREEN)
    new_data.x = x + 16
    new_data.y = y + 22
    view.append(new_data)

    return (new_label, new_data)

outdoor_y = TABS_Y + 66
(outdoorsensor_label, outdoorsensor_data) = TemperatureDisplay(view3, TABS_X, outdoor_y)
(sensors_label, sensor_data) = TemperatureDisplay(view3,TABS_X, TABS_Y)
layerVisibility("show", splash, view3)

# Update out Labels with display text.
text_box(
    sensors_label,
    TABS_Y,
    "",
    30,
)

text_box(
    outdoorsensor_label,
    outdoor_y,
    "",
    30
)
board.DISPLAY.show(splash)
time.sleep(1)

localtile_refresh = None
weather_refresh = None

# ------------- Code Loop ------------- #
while True:
    sensor_data.text = "Indoor Temperature:\n{:.0f}°F".format(get_Temperature(adt))


    if (not localtile_refresh) or (time.monotonic() - localtile_refresh) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time()
            localtile_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

     # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            res = pyportal.fetch(DATA_SOURCE)
            print("Response is", res)
            outdoorTemp = json.loads(res)
            outdoorsensor_data.text = f"Outdoor Temperature:\n{outdoorTemp["current"]["temp_f"]}°F"
            weather_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue