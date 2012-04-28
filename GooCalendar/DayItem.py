#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import calendar

import goocanvas
import pango


class DayItem(goocanvas.Group):
    """
    A canvas item representing a day.
    """
    def __init__(self, cal, **kwargs):
        super(DayItem, self).__init__()

        self.cal = cal
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.width = kwargs.get('width')
        self.height = kwargs.get('height')
        self.border_color = kwargs.get('border_color')
        self.body_color = kwargs.get('body_color')
        self.full_border = kwargs.get('full_border')
        self.date = kwargs.get('date')
        self.type = kwargs.get('type', 'month')
        self.show_indic = False
        self.line_height = None
        self.font_size = None
        self.lines = {}
        self.n_lines = 0

        # Create canvas items.
        self.border = goocanvas.Rect(parent=self)
        self.text = goocanvas.Text(parent=self)
        self.box = goocanvas.Rect(parent=self)
        self.indic = goocanvas.Rect(parent=self)

        if self.x is not None:
            self.update()

    def update(self):
        if self.type == 'month':
            self.font_size = max(self.height / 12, 10)
        else:
            self.font_size = max(self.height / 65, 10)
        text_padding = max(self.font_size / 2.5, 4)
        self.line_height = self.font_size + 2 * text_padding
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        font_descr.set_absolute_size(self.font_size * pango.SCALE)
        self.font = font_descr.to_string()
        date_tuple = self.date.timetuple()[:3]
        week_day = calendar.weekday(*date_tuple)
        day_name = calendar.day_name[week_day]
        caption = '%s %s' % (date_tuple[2], day_name)

        # Draw the border.
        self.border.set_property('x', self.x)
        self.border.set_property('y', self.y)
        self.border.set_property('width', self.width)
        self.border.set_property('height', self.height)
        self.border.set_property('stroke_color', self.border_color)
        self.border.set_property('fill_color', self.border_color)

        # Draw the title text.
        x = self.x + text_padding
        self.text.set_property('x', x)
        self.text.set_property('y', self.y + text_padding)
        self.text.set_property('font', self.font)
        self.text.set_property('text', caption)
        self.text.set_property('fill_color', self.title_text_color)

        # Print the "body" of the day.
        if self.full_border:
            box_x = self.x + 2
            box_y = self.y + self.line_height
            box_width = self.width - 4
            box_height = self.height - self.line_height - 3
        else:
            box_x = self.x + 1
            box_y = self.y + self.line_height
            box_width = self.width - 2
            box_height = self.height - self.line_height
        self.box.set_property('x', box_x)
        self.box.set_property('y', box_y)
        self.box.set_property('width', box_width)
        self.box.set_property('height', box_height)
        self.box.set_property('stroke_color', self.body_color)
        self.box.set_property('fill_color', self.body_color)

        self.n_lines = int(box_height / self.line_height)

        # Show an indicator in the title, if requested.
        if not self.show_indic:
            self.indic.set_property('visibility', goocanvas.ITEM_INVISIBLE)
            return

        self.indic.set_property('visibility', goocanvas.ITEM_VISIBLE)
        self.indic.set_property('x',
            self.x + self.width - self.line_height / 1.5)
        self.indic.set_property('y', self.y + self.line_height / 3)
        self.indic.set_property('width', self.line_height / 3)
        self.indic.set_property('height', self.line_height / 3)
        self.indic.set_property('stroke_color', self.title_text_color)
        self.indic.set_property('fill_color', self.title_text_color)

        # Draw a triangle.
        x1 = self.x + self.width - self.line_height / 1.5
        y1 = self.y + self.line_height / 3
        x2 = x1 + self.line_height / 6
        y2 = y1 + self.line_height / 3
        x3 = x1 + self.line_height / 3
        y3 = y1
        path = 'M%s,%s L%s,%s L%s,%s Z' % (x1, y1, x2, y2, x3, y3)
        self.indic.set_property('clip_path', path)
