#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.


class Event(object):
    """
    This class represents an event that can be displayed in the calendar.
    """

    def __init__(self, caption, start, end=None, **kwargs):
        assert caption is not None
        assert start   is not None
        self.id = None
        self.caption = caption
        self.start = start
        self.end = end
        self.all_day = kwargs.get('all_day', False)
        self.text_color = kwargs.get('text_color', None)
        self.bg_color = kwargs.get('bg_color', 'orangered')
        if end is None:
            self.all_day = True
            self.end = start
