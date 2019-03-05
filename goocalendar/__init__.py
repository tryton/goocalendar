# This file is part of GooCalendar.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GooCanvas', '2.0')
from ._calendar import Calendar
from ._event import Event, EventStore

__all__ = ['Calendar', 'EventStore', 'Event']
__version__ = '0.5'
