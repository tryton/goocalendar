# This file is part of GooCalendar.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import gobject

import util
from .util import total_ordering


@total_ordering
class Event(object):
    """
    This class represents an event that can be displayed in the calendar.
    """

    def __init__(self, caption, start, end=None, **kwargs):
        assert caption is not None
        assert start is not None
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
        if not self.end:
            return False
        return (self.end - self.start).days > 0

    def __eq__(self, other_event):
        if not isinstance(other_event, Event):
            raise NotImplemented
        return (self.start, self.end) == (other_event.start, other_event.start)

    def __lt__(self, other_event):
        if not isinstance(other_event, Event):
            raise NotImplemented
        return (self.start, self.end) < (other_event.start, other_event.start)


class EventStore(gobject.GObject):
    __gsignals__ = {
        'event-removed': (gobject.SIGNAL_RUN_FIRST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,)),
        'event-added': (gobject.SIGNAL_RUN_FIRST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,)),
        'events-cleared': (gobject.SIGNAL_RUN_FIRST,
            gobject.TYPE_NONE, ())}

    def __init__(self):
        super(EventStore, self).__init__()
        self._next_event_id = 0
        self._events = {}

    def remove(self, event):
        assert event is not None
        if event.id is None:
            return
        del self._events[event.id]
        self.emit('event-removed', event)

    def add(self, event):
        assert event is not None
        self.add_events([event])

    def add_events(self, events):
        for event in events:
            assert event.id is None
            self._events[self._next_event_id] = event
            event.id = self._next_event_id
            self._next_event_id += 1
        self.emit('event-added', events)

    def clear(self):
        self._events.clear()
        self._next_event_id = 0
        self.emit('events-cleared')

    def get_events(self, start=None, end=None):
        """
        Returns a list of all events that intersect with the given start
        and end times.
        """
        if not start and not end:
            return self._events.values()
        events = []
        for event in self._events.values():
            if util.event_intersects(event, start, end):
                events.append(event)
        return events
