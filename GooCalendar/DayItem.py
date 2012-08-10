#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import calendar

import goocanvas
import pango
import math


class DayItem(goocanvas.Group):
    """
    A canvas item representing a day.
    """

    def __init__(self, cal, **kwargs):
        super(DayItem, self).__init__()

        self.cal = cal
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.border_color = kwargs.get('border_color')
        self.body_color = kwargs.get('body_color')
        self.full_border = kwargs.get('full_border')
        self.date = kwargs.get('date')
        self.type = kwargs.get('type', 'month')
        self.show_indic = False
        self.lines = {}
        self.n_lines = 0
        self.title_text_color = ""
        self.line_height = 0

        # Create canvas items.
        self.border = goocanvas.Rect(parent=self)
        self.text = goocanvas.Text(parent=self)
        self.box = goocanvas.Rect(parent=self)
        self.indic = goocanvas.Rect(parent=self)

    def update(self):
        if not self.date:
            return

        date_tuple = self.date.timetuple()[:3]
        week_day = calendar.weekday(*date_tuple)
        day_name = calendar.day_name[week_day]
        caption = '%s %s' % (date_tuple[2], day_name)
        style = self.cal.get_style()
        font_descr = style.font_desc.copy()
        font = font_descr.to_string()
        self.text.set_property('font', font)
        self.text.set_property('text', caption)
        logical_height = self.text.get_natural_extents()[1][3]
        line_height = int(math.ceil(float(logical_height) / pango.SCALE))
        self.line_height = line_height

        # Draw the border.
        self.border.set_property('x', self.x)
        self.border.set_property('y', self.y)
        self.border.set_property('width', self.width)
        self.border.set_property('height', self.height)
        self.border.set_property('stroke_color', self.border_color)
        self.border.set_property('fill_color', self.border_color)

        # Draw the title text.
        padding_left = 2
        self.text.set_property('x', self.x + padding_left)
        self.text.set_property('y', self.y)
        self.text.set_property('fill_color', self.title_text_color)

        # Print the "body" of the day.
        if self.full_border:
            box_x = self.x + 2
            box_y = self.y + line_height
            box_width = max(self.width - 4, 0)
            box_height = max(self.height - line_height - 3, 0)
        else:
            box_x = self.x + 1
            box_y = self.y + line_height
            box_width = max(self.width - 2, 0)
            box_height = max(self.height - line_height, 0)
        self.box.set_property('x', box_x)
        self.box.set_property('y', box_y)
        self.box.set_property('width', box_width)
        self.box.set_property('height', box_height)
        self.box.set_property('stroke_color', self.body_color)
        self.box.set_property('fill_color', self.body_color)

        line_height_and_margin = line_height + 2  # 2px of margin per line
        self.n_lines = int(box_height / line_height_and_margin)

        # Show an indicator in the title, if requested.
        if not self.show_indic:
            self.indic.set_property('visibility', goocanvas.ITEM_INVISIBLE)
            return

        self.indic.set_property('visibility', goocanvas.ITEM_VISIBLE)
        self.indic.set_property('x',
            self.x + self.width - line_height / 1.5)
        self.indic.set_property('y', self.y + line_height / 3)
        self.indic.set_property('width', line_height / 3)
        self.indic.set_property('height', line_height / 3)
        self.indic.set_property('stroke_color', self.title_text_color)
        self.indic.set_property('fill_color', self.title_text_color)

        # Draw a triangle.
        x1 = self.x + self.width - line_height / 1.5
        y1 = self.y + line_height / 3
        x2 = x1 + line_height / 6
        y2 = y1 + line_height / 3
        x3 = x1 + line_height / 3
        y3 = y1
        path = 'M%s,%s L%s,%s L%s,%s Z' % (x1, y1, x2, y2, x3, y3)
        self.indic.set_property('clip_path', path)
