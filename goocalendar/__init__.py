# This file is part of GooCalendar.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import goocanvas
import pango

if not hasattr(goocanvas, 'Text'):
    goocanvas.Text = goocanvas.CanvasText

if hasattr(pango, 'Rectangle'):
    def getitem(self, i):
        return [self.x, self.y, self.width, self.height][i]
    pango.Rectangle.__getitem__ = getitem

from ._calendar import Calendar
from ._event import Event, EventStore

__all__ = ['Calendar', 'EventStore', 'Event']
__version__ = '0.5'
