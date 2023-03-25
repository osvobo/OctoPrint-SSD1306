import pytest
from time import sleep
from .SSD1306 import SSD1306

# Simple test of SSD1306

width = 128
height = 32
fontsize = 8
refresh_rate = 120
rows = round(height/fontsize)


class TestSSD1306:
    display = SSD1306(
        width=width,
        height=height,
        fontsize=fontsize,
        refresh_rate=refresh_rate,
    )

    def test_vars(self):
        assert self.display._width == width
        assert self.display._height == height
        assert self.display._fontsize == fontsize
        assert len(self.display._rows) == rows

    def test_write_row(self):
        # Should succeed when writing to rows within index.
        for i in range(0, rows):
            assert self.display.write_row(i, 'Line {}; '.format(i)*i) == None
            assert self.display._rows[i] == 'Line {}; '.format(i)*i
        # Write outside of index.
        with pytest.raises(IndexError):
            self.display.write_row(99, '')

    def test_clear_rows(self):
        # Clear all rows
        for i in range(0, rows):
            self.display.write_row(i, str(i))
        assert self.display.clear_rows() == None
        assert self.display._rows == ['']*rows
        # Clear one line and make sure only one line has been cleared.
        for i in range(0, rows):
            self.display.write_row(i, str(i))
        assert self.display.clear_rows(1) == None
        for i in range(0, rows):
            if i in [1]:
                assert self.display._rows[i] == ''
            else:
                assert self.display._rows[i] == str(i)
        # Clear two lines.
        for i in range(0, rows):
            self.display.write_row(i, str(i))
        assert self.display.clear_rows(1, 2) == None
        for i in range(0, rows):
            if i in [1, 2]:
                assert self.display._rows[i] == ''
            else:
                assert self.display._rows[i] == str(i)
        # Error when start is less than one
        with pytest.raises(IndexError):
            self.display.clear_rows(-1)
        # Error when end is less than start
        with pytest.raises(IndexError):
            self.display.clear_rows(2, 1)
        # Error when clearing outside of end index.
        with pytest.raises(IndexError):
            self.display.clear_rows(0, rows*10)

    def test_commit(self):
        assert self.display.commit() == None

    def test_thread(self):
        self.display.clear_rows()
        assert self.display.start() == None
        for i in range(0, rows):
            assert self.display.write_row(i, 'Line {}'.format(i)) == None
            assert self.display.commit() == None
            sleep(1/self.display._refresh_rate)
        assert self.display.clear_rows() == None
        self.display.stop() == None

    def test_change_params(self):
        self.display = SSD1306(
            width=width,
            height=2*height,
            fontsize=fontsize,
        )
        assert self.display._width == width
        assert self.display._height == 2*height
        assert self.display._fontsize == fontsize

    def test_change_fontsize(self):
        for i in [1, 2]:
            self.display = SSD1306(
                width=width,
                height=height,
                fontsize=i*fontsize,
            )
            assert self.display._fontsize == i*fontsize
            self.display.write_row(0, 'Test fontsize {}'.format(str(i)))
            self.display.commit()
            self.display.start()
            sleep(1/self.display._refresh_rate)
            self.display._image.save('test/larger_font{}.png'.format(str(i)))
            self.display.clear_rows()
            self.display.stop()

    def test_log(self):
        assert self.display.log('Test') == None
