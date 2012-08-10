#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from operator import add

import goocanvas
import pango

import util


class EventItem(goocanvas.Group):
    """
    A canvas item representing an event.
    """

    def __init__(self, cal, **kwargs):
        super(EventItem, self).__init__()

        self.cal = cal
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.width = kwargs.get('width')
        self.height = kwargs.get('height')
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color')
        self.event = kwargs.get('event')
        self.type = kwargs.get('type', 'leftright')
        self.time_format = kwargs.get('time_format')
        self.transparent = False
        self.no_caption = False

        # Create canvas items.
        self.box = goocanvas.Rect(parent=self)
        self.text = goocanvas.Text(parent=self)
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        self.font = font_descr.to_string()
        self.text.set_property('font', self.font)
        logical_height = self.text.get_natural_extents()[1][3]
        self.line_height = logical_height / pango.SCALE

        if self.x is not None:
            self.update()

    def update(self):
        if (self.event.all_day or self.cal.zoom == "month"
                or self.event.multidays):
            self.update_all_day_event()
        else:
            self.update_event()

    def update_event(self):
        self.width = max(self.width, 0)
        starttime = self.event.start.strftime(self.time_format)
        endtime = self.event.end.strftime(self.time_format)
        tooltip = '%s - %s\n%s' % (starttime, endtime, self.event.caption)

        # Do we have enough width for caption
        first_line = starttime + ' - ' + endtime
        self.text.set_property('text', first_line)
        logical_width = self.text.get_natural_extents()[1][2] / pango.SCALE
        if self.width < logical_width:
            first_line = starttime + ' - '

        second_line = self.event.caption
        self.text.set_property('text', second_line)
        logical_width = self.text.get_natural_extents()[1][2] / pango.SCALE
        if self.width < logical_width:
            second_line = None

        # Do we have enough height for whole caption
        if self.height >= (2 * self.line_height):
            caption = first_line
            if second_line:
                caption += '\n' + second_line
        elif self.height >= self.line_height:
            caption = first_line
        else:
            caption = ''
        caption = '' if self.no_caption else caption
        the_event_bg_color = self.event.bg_color

        # Choose text color.
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        if the_event_bg_color is not None:
            self.box.set_property('x', self.x)
            self.box.set_property('y', self.y)
            self.box.set_property('width', self.width)
            self.box.set_property('height', self.height)
            self.box.set_property('stroke_color', the_event_bg_color)
            bg_rgba_color = self.box.get_property('stroke_color_rgba')
            bg_colors = list(util.rgba_to_colors(bg_rgba_color))
            # We make background color 1/4 brighter (+64 over 255)
            bg_colors[:3] = map(min,
                map(add, bg_colors[:3], (64,) * 3), (255,) * 3)
            bg_colors = util.colors_to_rgba(*bg_colors)
            self.box.set_property('fill_color_rgba', bg_colors)

            # Alpha color is set to half of 255, i.e an opacity of 5O percents
            transparent_color = self.box.get_property('fill_color_rgba') - 128
            if self.transparent:
                self.box.set_property('stroke_color_rgba', transparent_color)
                self.box.set_property('fill_color_rgba', transparent_color)
            self.box.set_property('tooltip', tooltip)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('text', caption)
        self.text.set_property('fill_color', the_event_text_color)
        self.text.set_property('tooltip', tooltip)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (self.x, self.y, self.x, y2,
            x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)

    def update_all_day_event(self):
        self.width = max(self.width, 0)
        startdate = self.event.start.strftime('%x')
        starttime = self.event.start.strftime(self.time_format)
        if self.event.end:
            enddate = self.event.end.strftime('%x')
            endtime = self.event.end.strftime(self.time_format)

        if self.event.all_day:
            caption = self.event.caption
            if not self.event.end:
                tooltip = '%s\n%s' % (startdate, caption)
            else:
                tooltip = '%s - %s\n%s' % (startdate, enddate, caption)
        elif self.event.multidays:
            caption = '%s %s' % (starttime, self.event.caption)
            tooltip = '%s %s - %s %s\n%s' % (startdate, starttime, enddate,
                endtime, self.event.caption)
        else:
            caption = '%s %s' % (starttime, self.event.caption)
            tooltip = '%s - %s\n%s' % (starttime, endtime, self.event.caption)
        caption = '' if self.no_caption else caption
        the_event_bg_color = self.event.bg_color
        self.text.set_property('text', caption)
        logical_height = self.text.get_natural_extents()[1][3]
        self.height = logical_height / pango.SCALE

        # Choose text color.
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        if the_event_bg_color is not None:
            self.box.set_property('x', self.x)
            self.box.set_property('y', self.y)
            self.box.set_property('width', self.width)
            self.box.set_property('height', self.height)
            self.box.set_property('stroke_color', the_event_bg_color)
            bg_rgba_color = self.box.get_property('stroke_color_rgba')
            bg_colors = list(util.rgba_to_colors(bg_rgba_color))
            bg_colors[:3] = map(min,
                map(add, bg_colors[:3], (64,) * 3), (255,) * 3)
            bg_colors = util.colors_to_rgba(*bg_colors)
            self.box.set_property('fill_color_rgba', bg_colors)
            transparent_color = self.box.get_property('fill_color_rgba') - 128
            if self.transparent:
                self.box.set_property('stroke_color_rgba', transparent_color)
                self.box.set_property('fill_color_rgba', transparent_color)
            self.box.set_property('tooltip', tooltip)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('fill_color', the_event_text_color)
        self.text.set_property('tooltip', tooltip)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (
            self.x, self.y, self.x, y2, x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)
