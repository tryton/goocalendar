#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gobject

import util


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
        self.next_event_id = 0
        self.events = {}

    def remove(self, event):
        assert event is not None
        if event.id is None:
            return
        del self.events[event.id]
        self.emit('event-removed', event)

    def add(self, event):
        assert event is not None
        assert event.id is None
        self.events[self.next_event_id] = event
        event.id = self.next_event_id
        self.next_event_id += 1
        self.emit('event-added', event)

    def clear(self):
        self.events.clear()
        self.next_event_id = 0
        self.emit('events-cleared')

    def get_events(self, start=None, end=None):
        """
        Returns a list of all events that intersect with the given start
        and end times.
        """
        if not start and not end:
            return self.events.values()
        events = []
        for event in self.events.values():
            if util.event_intersects(event, start, end):
                events.append(event)
        return events
