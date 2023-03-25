import copy
import threading
from logging import DEBUG, ERROR, INFO, WARN
from time import sleep

import adafruit_ssd1306
import busio
from PIL import Image, ImageDraw, ImageFont

from octoprint_ssd1306oleddisplay.helpers import find_resource

try:
    from board import SCL, SDA
except:
    pass

# from octoprint_ssd1306display.helpers import find_resource


class SSD1306(threading.Thread):
    _lock = threading.Lock()
    _stop = False
    daemon = True
    _rows = []
    _committed_rows = []

    def __init__(
        self,
        width=128,
        height=32,
        fontsize=8,
        refresh_rate=1,
        logger=None,
    ):
        super(SSD1306, self).__init__()

        # Setup variables
        self._height = height
        self._width = width
        self._fontsize = fontsize
        self._y_offset = 0
        self._logger = logger
        self._refresh_rate = refresh_rate
        # self._font = ImageFont.load_default()
        self._font = ImageFont.truetype(find_resource(
            'font/PressStart2P.ttf'), self._fontsize)
        self._image = Image.new('1', (self._width, self._height))
        self._draw = ImageDraw.Draw(self._image)
        # Start with the same number of rows as set by dimensions.
        self._rows = [''] * round(self._height/self._fontsize)

        try:
            i2c = busio.I2C(SCL, SDA)
            self._display = adafruit_ssd1306.SSD1306_I2C(
                self._width,
                self._height,
                i2c,
            )
            self.log('Display initialized', level=DEBUG)
        except:
            self.log('Failed to initialize display', level=WARN)

        self.log(
            'Width: {}, height: {}'.format(self._width, self._height), level=DEBUG)

    # Clear content.
    def clear_rows(self, start=None, end=None):
        """
        Clear content.
        - All rows if no arguments are set.
        - From first row if set.
        - Only one row if end is not set.
        - Until row `end` if set.
        - Until end if `end=-1`.
        """
        if start is None and end is None:
            _start = 0
            _end = len(self._rows)
        else:
            if start == None:
                _start = 0
            elif start <= len(self._rows) and start >= 0:
                _start = start
            else:
                self.log('Start is out of range.', level=ERROR)
                raise IndexError('Start out of range')

            if end == None:
                _end = _start+1
            elif end == -1:
                _end = len(self._rows)
            elif end <= len(self._rows):
                _end = end+1
            else:
                self.log('End is out of range.', level=ERROR)
                raise IndexError('End out of range')
            
            if _end <= _start:
                raise IndexError('End should not be smaller than start.')

        for i in range(_start, _end):
            self._rows[i] = ''

    # Write content to row.
    def write_row(self, row, text):
        """ Write data to row """
        if (row < len(self._rows)):
            self._rows[row] = text
        else:
            self.log('Row index too large, {} > {}'.format(
                row, len(self._rows)), level=INFO)
            raise IndexError('Row index out of range, got {} but should be in range(0, {})'.format(
                row, len(self._rows)))

    def commit(self):
        """ Send data to be shown on the display. """
        with self._lock:
            self._committed_rows = copy.copy(self._rows)
        self.log(self._committed_rows, level=DEBUG)

    def run(self):
        """ Loop that update what is shown on the display """
        while not self._stop:
            with self._lock:
                rows = copy.copy(self._committed_rows)
            # Clear display
            self._draw.rectangle((0, 0, self._width, self._height), fill=0)
            # Draw text on image
            for (r, text) in enumerate(rows):
                self._draw.text(
                    (0, r * self._fontsize + self._y_offset), text, font=self._font, fill=200)
            try:
                self._display.image(self._image)  # Send image to display
                self._display.show()  # Show
            except:
                # self._image.save('test/img.png')
                self.log('Failed to send to display', level=DEBUG)
            sleep(1/self._refresh_rate)

    def stop(self):
        """ Shutdown. Stop thread and empty screen. """
        self._stop = True
        self.clear_rows()
        try:
            self._display.fill(0)
            self._display.show()
        except:
            self.log('Failed to clear display')

    def log(self, message, level=INFO):
        """ Log message. Can optionally set level."""
        if self._logger != None:
            if (level is WARN):
                self._logger.warn(message)
            elif level is DEBUG:
                self._logger.debug(message)
            else:
                self._logger.info(message)
        else:
            print('{}: {}'.format(level, message))
