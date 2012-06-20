#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import goocanvas
import pango


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

        # Create canvas items.
        self.box = goocanvas.Rect(parent=self)
        self.box2 = goocanvas.Rect(parent=self)
        self.text = goocanvas.Text(parent=self)

        if self.x is not None:
            self.update()

    def update(self):
        if self.event.all_day or self.cal.zoom == "month":
            self.update_all_day_event()
        else:
            self.update_event()

    def update_event(self):
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        self.width = max(self.width, 0)
        self.font = font_descr.to_string()
        caption = self.event.caption
        the_event_bg_color = self.event.bg_color

        # Choose text color.
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        # Draw the event background.
        radius = 4
        if self.type == 'mid':
            self.box2.set_property('visibility', goocanvas.ITEM_INVISIBLE)
            radius = 0
        elif self.type == 'topbottom':
            self.box2.set_property('visibility', goocanvas.ITEM_INVISIBLE)
        elif self.type == 'top':
            self.box2.set_property('visibility', goocanvas.ITEM_VISIBLE)
            self.box2.set_property('y', self.y)
        elif self.type == 'bottom':
            self.box2.set_property('visibility', goocanvas.ITEM_VISIBLE)
            self.box2.set_property('y', self.y + self.height - radius)

        if the_event_bg_color is not None:
            self.box.set_property('x', self.x)
            self.box.set_property('y', self.y)
            self.box.set_property('width', self.width)
            self.box.set_property('height', self.height)
            self.box.set_property('radius_x', radius)
            self.box.set_property('radius_y', radius)
            self.box.set_property('stroke_color', the_event_bg_color)
            self.box.set_property('fill_color', the_event_bg_color)

            # Box 2 hides the rounded corners of box1.
            self.box2.set_property('x', self.x)
            self.box2.set_property('width', self.width)
            self.box2.set_property('height', radius)
            self.box2.set_property('stroke_color', the_event_bg_color)
            self.box2.set_property('fill_color', the_event_bg_color)

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

        # Draw the event background.
        radius = self.height / 4
        if self.type == 'mid':
            self.box2.set_property('visibility', goocanvas.ITEM_INVISIBLE)
            radius = 0
        elif self.type == 'leftright':
            self.box2.set_property('visibility', goocanvas.ITEM_INVISIBLE)
        elif self.type == 'right':
            self.box2.set_property('visibility', goocanvas.ITEM_VISIBLE)
            self.box2.set_property('x', self.x)
        elif self.type == 'left':
            self.box2.set_property('visibility', goocanvas.ITEM_VISIBLE)
            self.box2.set_property('x', self.x + self.width - radius)

        if the_event_bg_color is not None:
            self.box.set_property('x', self.x)
            self.box.set_property('y', self.y)
            self.box.set_property('width', self.width)
            self.box.set_property('height', self.height)
            self.box.set_property('radius_x', radius)
            self.box.set_property('radius_y', radius)
            self.box.set_property('stroke_color', the_event_bg_color)
            self.box.set_property('fill_color', the_event_bg_color)

            # Box 2 hides the rounded corners of box1.
            self.box2.set_property('y', self.y)
            self.box2.set_property('width', radius)
            self.box2.set_property('height', self.height)
            self.box2.set_property('stroke_color', the_event_bg_color)
            self.box2.set_property('fill_color', the_event_bg_color)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('fill_color', the_event_text_color)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (
            self.x, self.y, self.x, y2, x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)
