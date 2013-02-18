#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime

import gtk

import goocalendar


def on_event_pressed(calendar, event, event_store):
    print "Event %s was pressed" % event.caption


def on_day_selected(calendar, day):
    print "Day %s was selected" % day


def on_key_pressed(widget, event):
    if (event.state & gtk.gdk.CONTROL_MASK and
            event.keyval == gtk.gdk.keyval_from_name('l')):
        if widget.view == 'week':
            widget.set_view('month')
        else:
            widget.set_view('week')

window = gtk.Window()
event_store = goocalendar.EventStore()
calendar = goocalendar.Calendar(event_store)
calendar.set_has_tooltip(True)

# Normal events.
event = goocalendar.Event('Event number 1',
    datetime.datetime(2007, 10, 8, 02),
    datetime.datetime(2007, 10, 8, 17),
    bg_color='lightgreen')
event_store.add(event)
event = goocalendar.Event('Event number 2',
    datetime.datetime(2007, 10, 8, 12),
    datetime.datetime(2007, 10, 8, 14),
    bg_color='lightblue')
event_store.add(event)
event = goocalendar.Event('Event number 3',
    datetime.datetime(2007, 10, 8, 15),
    datetime.datetime(2007, 10, 8, 16, 30),
    bg_color='lightgrey')
event_store.add(event)
event = goocalendar.Event('Event number 3b',
    datetime.datetime(2007, 10, 8, 15, 30),
    datetime.datetime(2007, 10, 8, 17, 15),
    bg_color='lightgrey')
event_store.add(event)
event = goocalendar.Event('Event number 4',
    datetime.datetime(2007, 10, 8, 17),
    datetime.datetime(2007, 10, 8, 18),
    bg_color='yellow')
event_store.add(event)

# A normal multi-day event.
event = goocalendar.Event('Long Event',
    datetime.datetime(2007, 10, 9),
    datetime.datetime(2007, 10, 11))
event_store.add(event)

# The following events are all-day events and displayed differently in
# week mode.
event = goocalendar.Event('One-day Event', datetime.datetime(2007, 10, 9))
event_store.add(event)
event = goocalendar.Event('Four-day Event',
    datetime.datetime(2007, 10, 9),
    datetime.datetime(2007, 10, 12),
    all_day=True,
    bg_color='navy',
    text_color='white')
event_store.add(event)

calendar.select(datetime.date(2007, 10, 8))
window.add(calendar)
window.set_size_request(400, 400)
window.show_all()

window.connect('delete-event', gtk.main_quit)
calendar.connect('event-pressed', on_event_pressed, event_store)
calendar.connect('day-selected', on_day_selected)
calendar.connect('key-press-event', on_key_pressed)
gtk.main()
