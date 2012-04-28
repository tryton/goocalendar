#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import goocanvas
import pango


class TimelineItem(goocanvas.Group):
    """
    A canvas item representing a timeline.
    """
    def __init__(self, cal, **kwargs):
        super(TimelineItem, self).__init__()

        self.cal = cal
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.width = kwargs.get('width')
        self.height = kwargs.get('height')
        self.line_color = kwargs.get('line_color')
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color')

        # Create canvas items.
        self.timeline_rect = {}
        self.timeline_text = {}
        for n in range(0, 24):
            caption = '%s:00' % n
            self.timeline_rect[n] = goocanvas.Rect(parent=self)
            self.timeline_text[n] = goocanvas.Text(parent=self, text=caption)

        if self.x is not None:
            self.update()

    def update(self):
        text_padding = max(self.width / 20, 4)
        text_width = self.width - 2 * text_padding
        text_height = text_width / 5
        line_height = self.height / 24
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        font_descr.set_absolute_size(text_height * pango.SCALE)
        font = font_descr.to_string()

        # Draw the timeline.
        for n in range(0, 24):
            rect = self.timeline_rect[n]
            text = self.timeline_text[n]
            y = self.y + n * line_height

            rect.set_property('x', self.x)
            rect.set_property('y', y)
            rect.set_property('width', self.width)
            rect.set_property('height', line_height)
            rect.set_property('stroke_color', self.line_color)
            rect.set_property('fill_color', self.bg_color)

            text.set_property('x', self.x + text_padding)
            text.set_property('y', y + text_padding)
            text.set_property('font', font)
            text.set_property('fill_color', self.text_color)
