#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import goocanvas
import pango
import math


class TimelineItem(goocanvas.Group):
    """
    A canvas item representing a timeline.
    """

    def __init__(self, cal, **kwargs):
        super(TimelineItem, self).__init__()

        self.cal = cal
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.line_color = kwargs.get('line_color')
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color')

        # Create canvas items.
        self.timeline_rect = {}
        self.timeline_text = {}
        for n in range(24):
            hour = str(n).zfill(2)
            caption = hour + ':00'
            self.timeline_rect[n] = goocanvas.Rect(parent=self)
            self.timeline_text[n] = goocanvas.Text(parent=self, text=caption)

        if self.x is not None:
            self.update()

    @property
    def width(self):
        style = self.cal.get_style()
        font = style.font_desc

        # Find the maximal padding and width of texts
        ink_padding_left = 0
        ink_max_width = 0
        for n in range(24):
            self.timeline_text[n].set_property('font', font)
            natural_extents = self.timeline_text[n].get_natural_extents()
            ink_rect = natural_extents[0]
            ink_padding_left = max(ink_padding_left, ink_rect[0])
            ink_max_width = max(ink_max_width, ink_rect[2])
        self._width = int(math.ceil(float(ink_padding_left + ink_max_width)
            / pango.SCALE))
        return self._width

    @property
    def line_height(self):
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        pango_size = font_descr.get_size()
        logical_height = 0
        ink_padding_top = 0
        for n in range(24):
            natural_extents = self.timeline_text[n].get_natural_extents()
            logical_rect = natural_extents[1]
            logical_height = max(logical_height, logical_rect[3])
            ink_rect = natural_extents[0]
            ink_padding_top = max(ink_padding_top, ink_rect[0])
        line_height = int(math.ceil(float(logical_height) / pango.SCALE))
        
        # If we have more vertical space, use it and center the text
        self.padding_top = 0
        if line_height < self.height / 24:
            line_height = self.height / 24
            pango_size = self.cal.get_style().font_desc.get_size()
            padding_top = (line_height - pango_size / pango.SCALE) / 2
            padding_top -= int(math.ceil(float(ink_padding_top) / pango.SCALE))
            self.padding_top = padding_top
        return line_height
   
    def update(self):
        line_height = self.line_height
        
        # Draw the timeline.
        for n in range(24):
            rect = self.timeline_rect[n]
            text = self.timeline_text[n]
            y = self.y + n * line_height

            rect.set_property('x', self.x)
            rect.set_property('y', y)
            rect.set_property('width', self.width)
            rect.set_property('height', line_height)
            rect.set_property('stroke_color', self.line_color)
            rect.set_property('fill_color', self.bg_color)

            text.set_property('x', self.x)
            text.set_property('y', y + self.padding_top)
            text.set_property('fill_color', self.text_color)
