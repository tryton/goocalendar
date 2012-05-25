#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime

import gtk

import GooCalendar


def on_event_clicked(calendar, event, event_store):
    print "Event %s was clicked" % event.caption
    event_store.remove(event)


def on_day_selected(calendar, day):
    print "Day %s was clicked" % day

window = gtk.Window()
event_store = GooCalendar.EventStore()
calendar = GooCalendar.Calendar(event_store)

event_store.add(GooCalendar.Event("Bake",
        datetime.datetime(2007, 10, 16, 17, 0, 0),
        datetime.datetime(2007, 10, 16, 18, 0, 0)))

event_store.add(GooCalendar.Event("Ethiopian Feast Night",
        datetime.datetime(2007, 10, 16, 19, 30, 0),
        datetime.datetime(2007, 10, 16, 22, 30, 0)))

window.add(calendar)
window.set_size_request(400, 400)
window.show_all()

window.connect('delete-event', gtk.main_quit)
calendar.connect('event-clicked', on_event_clicked, event_store)
calendar.connect('day-selected',  on_day_selected)
gtk.main()
