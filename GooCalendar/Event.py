#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from util import total_ordering


@total_ordering
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
        self.event_items = []
        if end is None:
            self.all_day = True

    @property
    def multidays(self):
        return (not self.end or (self.end - self.start).days > 0)

    def __eq__(self, other_event):
        if not isinstance(other_event, Event):
            raise NotImplemented
        return (self.start, self.end) == (other_event.start, other_event.start)

    def __lt__(self, other_event):
        if not isinstance(other_event, Event):
            raise NotImplemented
        return (self.start, self.end) < (other_event.start, other_event.start)
