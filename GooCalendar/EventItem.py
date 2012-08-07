#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
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

        # Create canvas items.
        self.box = goocanvas.Rect(parent=self)
        self.text = goocanvas.Text(parent=self)

        if self.x is not None:
            self.update()

    def update(self):
        if (self.event.all_day or self.cal.zoom == "month"
                or self.event.multidays):
            self.update_all_day_event()
        else:
            self.update_event()

    def update_event(self):
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        self.width = max(self.width, 0)
        self.font = font_descr.to_string()
        starttime = self.event.start.strftime(self.time_format)
        endtime = self.event.end.strftime(self.time_format)
        caption = '%s - %s\n%s' % (starttime, endtime, self.event.caption)
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
            self.box.set_property('fill_color', the_event_bg_color)
            # Alpha color is set to half of 255, i.e an opacity of 5O percents
            transparent_color = self.box.get_property('fill_color_rgba') - 128
            if self.transparent:
                self.box.set_property('stroke_color_rgba', transparent_color)
                self.box.set_property('fill_color_rgba', transparent_color)
            self.box.set_property('tooltip', caption)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('font', self.font)
        self.text.set_property('text', caption)
        self.text.set_property('fill_color', the_event_text_color)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (self.x, self.y, self.x, y2,
            x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)

    def update_all_day_event(self):
        self.width = max(self.width, 0)
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        self.font = font_descr.to_string()
        starttime = self.event.start.strftime(self.time_format)
        endtime = self.event.end.strftime(self.time_format)
        if self.event.multidays and not self.event.all_day:
            caption = '%s - %s %s' % (starttime, endtime, self.event.caption)
        else:
            caption = self.event.caption
        the_event_bg_color = self.event.bg_color
        self.text.set_property('font', self.font)
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
            self.box.set_property('fill_color', the_event_bg_color)
            transparent_color = self.box.get_property('fill_color_rgba') - 128
            if self.transparent:
                self.box.set_property('stroke_color_rgba', transparent_color)
                self.box.set_property('fill_color_rgba', transparent_color)
            self.box.set_property('tooltip', caption)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('fill_color', the_event_text_color)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (
            self.x, self.y, self.x, y2, x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)
