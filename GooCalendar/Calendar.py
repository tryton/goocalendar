#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import time
import datetime
import calendar

import gtk
import gobject
import goocanvas
import pango

import util
from DayItem      import DayItem
from EventItem    import EventItem
from TimelineItem import TimelineItem


class Calendar(goocanvas.Canvas):
    ZOOM_LEVELS = ["month", "week"]

    def __init__(self, event_store=None, zoom="month"):
        super(Calendar, self).__init__()
        self.cal = calendar.Calendar(calendar.SUNDAY)
        self.today = time.localtime(time.time())[:3]
        self.selected_date = self.today
        self.selected_day = None
        self.bg_rect = None
        self.timeline = None
        self.line_height = 0
        self.realized = False
        self.event_store = None
        self._event_removed_sigid = None
        self._event_added_sigid = None
        self.set_event_store(event_store)
        self.event_items = []
        assert zoom in self.ZOOM_LEVELS
        self.zoom = zoom
        self.set_bounds(0, 0, 200, 200)
        self.set_flags(gtk.CAN_FOCUS)
        self.set_events(gtk.gdk.EXPOSURE_MASK
            | gtk.gdk.BUTTON_PRESS_MASK
            | gtk.gdk.BUTTON_RELEASE_MASK
            | gtk.gdk.POINTER_MOTION_MASK
            | gtk.gdk.POINTER_MOTION_HINT_MASK
            | gtk.gdk.KEY_PRESS_MASK
            | gtk.gdk.KEY_RELEASE_MASK
            | gtk.gdk.ENTER_NOTIFY_MASK
            | gtk.gdk.LEAVE_NOTIFY_MASK
            | gtk.gdk.FOCUS_CHANGE_MASK)
        self.connect_after('realize', self.on_realize)
        self.connect('size-allocate', self.on_size_allocate)
        self.connect('key-press-event', self.on_key_press_event)

        # Initialize background and days and add them to canvas
        root = self.get_root_item()
        style = self.get_style()
        color = util.color_to_string(style.bg[gtk.STATE_PRELIGHT])
        self.bg_rect = goocanvas.Rect(parent=root, x=0, y=0, \
            stroke_color=color, fill_color=color)
        self.days = []
        while len(self.days) < 42: # 6 rows of 7 days
            box = DayItem(self)
            root.add_child(box)
            box.connect('button_press_event', self.on_button_press_event)
            self.days.append(box)

    def select_from_tuple(self, new_date):
        old_date = self.selected_date
        old_day = self.selected_day
        self.selected_date = new_date[:3]
        page_changed = False
        if self.zoom == "month":
            page_changed = old_date[1] != new_date[1]
        if self.zoom == "week":
            page_changed = True  # Good enough for now...

        # This is slow: When the month was changed we need to update
        # the entire canvas.
        if old_day is None or page_changed:
            self.update()
            self.emit('day-selected', self.get_selected_date())
            return

        # This is fast: Update only the old and newly selected days.
        # Find the canvas item that corresponds to the new date.
        weeks = self.cal.monthdayscalendar(*new_date[:2])
        found = -1
        for weekno, week in enumerate(weeks):
            for dayno, day in enumerate(week):
                if day == new_date[2]:
                    found = weekno * 7 + dayno
                    break
            if found != -1:
                break

        # Swap border colors.
        new_day = self.days[found]
        old_border_color = old_day.border_color
        old_day.full_border = False
        old_day.border_color = new_day.border_color
        new_day.border_color = old_border_color
        new_day.full_border = True

        # Redraw.
        old_day.update()
        new_day.update()
        self.selected_day = new_day
        self.emit('day-selected', self.get_selected_date())

    def select(self, new_time):
        self.select_from_tuple(new_time.timetuple())

    def select_previous_page(self):
        date = datetime.datetime(*self.selected_date)
        if self.zoom == "month":
            selected_date = util.previous_month(self.cal, date).timetuple()[:3]
        elif self.zoom == "week":
            selected_date = util.previous_week(self.cal, date).timetuple()[:3]
        self.select_from_tuple(selected_date)

    def select_next_page(self):
        date = datetime.datetime(*self.selected_date)
        if self.zoom == "month":
            date = util.next_month(self.cal, date)
        elif self.zoom == "week":
            date = util.next_week(self.cal, date)
        self.select(date)

    def set_zoom(self, level):
        assert level in self.ZOOM_LEVELS
        self.zoom = level
        self.update()

    def get_selected_date(self):
        return datetime.datetime(*self.selected_date)

    def set_event_store(self, event_store):
        # Disconnect previous event store if any
        if self.event_store:
            self.event_store.disconnect(self._event_removed_sigid)
            self.event_store.disconnect(self._event_added_sigid)

        # Set and connect new event_store
        self.event_store = event_store
        self.update()
        if not event_store:
            return
        self._event_removed_sigid = self.event_store.connect('event-removed',
            self.on_event_store_event_removed)
        self._event_added_sigid = self.event_store.connect('event-added',
            self.on_event_store_event_added)

    def on_realize(self, *args):
        self.realized = True
        self.grab_focus(self.get_root_item())
        self.on_size_allocate(*args)

    def on_size_allocate(self, *args):
        alloc = self.get_allocation()
        if not self.realized or alloc.width < 10 or alloc.height < 10:
            return
        self.set_bounds(0, 0, alloc.width, alloc.height)
        self.update()

    def update(self):
        if not self.realized:
            return
        self.draw_background()
        if self.zoom == "month":
            self.draw_month()
        elif self.zoom == "week":
            self.draw_week()
        self.draw_events()

    def draw_background(self):
        x, y, w, h = self.get_bounds()
        self.bg_rect.set_property('width', w)
        self.bg_rect.set_property('height', h)

    def draw_week(self):
        """
        Draws the currently selected week.
        """
        style = self.get_style()
        text_color = util.color_to_string(style.fg[gtk.STATE_NORMAL])
        border_color = util.color_to_string(style.mid[gtk.STATE_NORMAL])
        body_color = util.color_to_string(style.light[gtk.STATE_ACTIVE])
        selected_border_color = util.color_to_string(
            style.mid[gtk.STATE_SELECTED])
        today_body_color = 'ivory'
        x, y, w, h = self.get_bounds()
        timeline_w = w / 12
        day_width = (w - timeline_w) / 7
        day_height = h

        # Redraw all days.
        weeks = util.my_monthdatescalendar(self.cal, *self.selected_date)
        for weekno, week in enumerate(weeks):
            # Hide all days that are not part of the current week.
            weekdays = [date.timetuple()[:3] for date in week]
            if self.selected_date[:3] not in weekdays:
                for dayno, date in enumerate(week):
                    box = self.days[weekno * 7 + dayno]
                    box.set_property('visibility', goocanvas.ITEM_INVISIBLE)
                continue

            # Draw the days that are part of the current week.
            for dayno, date in enumerate(week):
                # Highlight the day according to it's selection.
                current_date = date.timetuple()[:3]
                selected = current_date == self.selected_date
                if selected:
                    the_border_color = selected_border_color
                else:
                    the_border_color = border_color
                if current_date == self.today:
                    the_body_color = today_body_color
                else:
                    the_body_color = body_color

                # Draw.
                box = self.days[weekno * 7 + dayno]
                box.x = day_width * dayno + timeline_w
                box.y = 0
                box.width = day_width - 2
                box.height = day_height
                box.type = 'week'
                box.date = date
                box.full_border = selected
                box.border_color = the_border_color
                box.body_color = the_body_color
                box.title_text_color = text_color
                box.event_text_color = text_color
                box.set_property('visibility', goocanvas.ITEM_VISIBLE)
                box.update()

                if selected:
                    self.selected_day = box

    def draw_month(self):
        """
        Draws the currently selected month.
        """
        style = self.get_style()
        x1, y1, w, h = self.get_bounds()
        day_width = w / 7
        day_height = (h - self.line_height) / 6
        text_height = max(day_height / 12, 10)
        font_descr = style.font_desc.copy()
        font_descr.set_absolute_size(text_height * pango.SCALE)
        text_color = util.color_to_string(style.fg[gtk.STATE_NORMAL])
        inactive_text_color = util.color_to_string(
            style.fg[gtk.STATE_INSENSITIVE])
        border_color = util.color_to_string(style.mid[gtk.STATE_NORMAL])
        selected_border_color = util.color_to_string(
            style.mid[gtk.STATE_SELECTED])
        inactive_border_color = util.color_to_string(
            style.bg[gtk.STATE_PRELIGHT])
        body_color = util.color_to_string(style.light[gtk.STATE_ACTIVE])
        today_body_color = 'ivory'

        # Hide the timeline.
        if self.timeline is not None:
            self.timeline.set_property('visibility', goocanvas.ITEM_INVISIBLE)

        # Draw the grid.
        y_pos = self.line_height
        weeks = util.my_monthdatescalendar(self.cal, *self.selected_date)
        for weekno, week in enumerate(weeks):
            for dayno, date in enumerate(week):
                # The color depends on whether each day is part of the
                # current month.
                year, month, day = date.timetuple()[:3]
                if (year, month) != self.selected_date[:2]:
                    the_border_color = inactive_border_color
                    the_text_color = inactive_text_color
                else:
                    the_border_color = border_color
                    the_text_color = text_color

                # Highlight the day according to it's selection.
                current_date = date.timetuple()[:3]
                selected = current_date == self.selected_date
                if selected:
                    the_border_color = selected_border_color
                if current_date == self.today:
                    the_body_color = today_body_color
                else:
                    the_body_color = body_color

                # Draw a box for the day.
                box = self.days[weekno * 7 + dayno]
                box.x = day_width * dayno
                box.y = y_pos
                box.width = day_width - 2
                box.height = day_height - 2
                box.date = date
                box.full_border = selected
                box.border_color = the_border_color
                box.body_color = the_body_color
                box.title_text_color = the_text_color
                box.event_text_color = the_text_color
                box.type = 'month'
                box.set_property('visibility', goocanvas.ITEM_VISIBLE)
                box.update()

                if selected:
                    self.selected_day = box

            y_pos += day_height

    def _get_day_item(self, find_date):
        weeks = util.my_monthdatescalendar(self.cal, *find_date.timetuple())
        for weekno, week in enumerate(weeks):
            for dayno, date in enumerate(week):
                if date == find_date:
                    return self.days[weekno * 7 + dayno]
        raise Exception('Day not found: %s' % (find_date))

    def _get_day_items(self, event):
        """
        Given an event, this method returns a list containing the
        DayItem corresponding with each day on which the event takes
        place.
        Days that are currently not in the view are not returned.
        """
        weeks = util.my_monthdatescalendar(self.cal, *self.selected_date)
        start = event.start.timetuple()[:3]
        end = event.end.timetuple()[:3]
        days = []
        for weekno, week in enumerate(weeks):
            if self.zoom == "week":
                weekdays = [date.timetuple()[:3] for date in week]
                if self.selected_date not in weekdays:
                    continue
            for dayno, date in enumerate(week):
                date = date.timetuple()[:3]
                if date >= start and date <= end:
                    days.append(self.days[weekno * 7 + dayno])
                if date == end:
                    return days
        if len(days) > 0:
            return days
        raise Exception('Days not found: %s %s' % (event.start, event.end))

    def _find_free_line(self, days):
        for line in range(days[0].n_lines):
            free = True
            for day in days:
                if line in day.lines:
                    free = False
                    break
            if free:
                return line
        return None

    def draw_events(self):
        # Clear previous events.
        for item in self.event_items:
            self.get_root_item().remove_child(item)
        self.event_items = []
        for day in self.days:
            day.lines.clear()
            day.show_indic = False
            day.update()

        if not self.event_store:
            return

        if self.zoom == "month":
            weeks = util.my_monthdatescalendar(self.cal, *self.selected_date)
            dates = []
            for week in weeks:
                dates += week
        else:
            dates = util.my_weekdatescalendar(self.cal, *self.selected_date)

        # Retrieve a list of all events in the current time span,
        # and sort them by event length.
        start = datetime.datetime(*dates[0].timetuple()[:3])
        end = datetime.datetime(*dates[-1].timetuple()[:3])
        events = self.event_store.get_events(start, end)
        events.sort(util.event_days, reverse=True)

        # Draw all-day events, longest event first.
        max_y = self.selected_day.line_height
        non_all_day_events = []
        for event in events:
            # Handle non-all-day events differently in week mode.
            if self.zoom == "week" and not event.all_day:
                non_all_day_events.append(event)
                continue

            # Find a line that is free in all of the days.
            days = self._get_day_items(event)
            free_line = self._find_free_line(days)
            if free_line is None:
                for day in days:
                    day.show_indic = True
                    day.update()
                continue

            max_line_height = max(x.line_height for x in days)
            max_y = max((free_line + 2) * max_line_height + 2, max_y)
            for day in days:
                day.lines[free_line] = 1

            # Split days into weeks.
            weeks = []
            week_start = 0
            week_end = 0
            while week_end < len(days):
                day = days[week_start]
                weekday = (day.date.weekday() - self.cal.firstweekday) % 7
                week_end = week_start + (7 - weekday)
                week = days[week_start:week_end]
                weeks.append(week)
                #print "Week:", weekday, [d.date for d in week], start, end
                week_start = week_end

            for week in weeks:
                dayno = 0
                day = week[dayno]
                event_item = EventItem(self, event=event)
                event_item.connect('button_press_event',
                                   self.on_event_item_button_press_event)
                self.event_items.append(event_item)
                self.get_root_item().add_child(event_item)
                event_item.x = day.x
                event_item.y = day.y + (free_line + 1) * day.line_height + 2
                event_item.width = (day.width + 2) * len(week)
                event_item.height = day.line_height
                week_start = week[0].date
                week_end = week[-1].date
                if (event.start.date() < week_start
                        and event.end.date() > week_end):
                    event_item.type = 'mid'
                    event_item.width -= 3
                elif event.start.date() < week_start:
                    event_item.type = 'right'
                    event_item.width -= 4
                elif event.end.date() > week_end:
                    event_item.type = 'left'
                    event_item.x += 2
                    event_item.width -= 4
                else:
                    event_item.x += 2
                    event_item.width -= 6
                    event_item.type = 'leftright'
                event_item.update()

        if self.zoom != "week":
            return

        # Redraw the timeline.
        style = self.get_style()
        text_color = util.color_to_string(style.fg[gtk.STATE_NORMAL])
        border_color = util.color_to_string(style.mid[gtk.STATE_NORMAL])
        body_color = util.color_to_string(style.light[gtk.STATE_ACTIVE])
        if self.timeline is None:
            self.timeline = TimelineItem(self)
            self.get_root_item().add_child(self.timeline)
        self.timeline.set_property('visibility', goocanvas.ITEM_VISIBLE)
        x, y, w, h = self.get_bounds()
        self.timeline.x = x
        self.timeline.y = max_y
        self.timeline.width = w / 12 - 2
        self.timeline.height = h - max_y - 2
        self.timeline.line_color = body_color
        self.timeline.bg_color = border_color
        self.timeline.text_color = text_color
        self.timeline.update()

        # Draw non-all-day events.
        for date in dates:
            date_start = datetime.datetime(*date.timetuple()[:3])
            date_end = date_start + datetime.timedelta(1)
            day = self._get_day_item(date)
            day_events = util.get_intersection_list(non_all_day_events,
                date_start, date_end)
            columns = []
            column = 0

            # Sort events into columns.
            remaining_events = day_events[:]
            while len(remaining_events) > 0:
                columns.append([remaining_events[0]])
                for event in remaining_events:
                    intersections = util.count_intersections(columns[-1],
                        event.start, event.end)
                    if intersections == 0:
                        columns[-1].append(event)
                for event in columns[-1]:
                    remaining_events.remove(event)

            # Walk through all columns.
            for columnno, column in enumerate(columns):
                for event in column:
                    # Crop the event to the current day.
                    event1_start = max(event.start, date_start)
                    event1_end = min(event.end, date_end)

                    parallel = util.count_parallel_events(day_events,
                        event1_start, event1_end)

                    # Draw.
                    top_offset = event1_start - date_start
                    bottom_offset = event1_end - event1_start
                    top_offset_mins = top_offset.seconds / 60
                    bottom_offset_mins = ((bottom_offset.days * 24 * 60)
                        + bottom_offset.seconds / 60)

                    event_item = EventItem(self, event=event)
                    event_item.connect('button_press_event',
                        self.on_event_item_button_press_event)
                    self.event_items.append(event_item)
                    self.get_root_item().add_child(event_item)
                    minute_height = self.timeline.height / 24 / 60
                    y_off1 = top_offset_mins * minute_height
                    y_off2 = bottom_offset_mins * minute_height
                    column_width = day.width / parallel
                    event_item.x = day.x + (columnno * column_width) + 2
                    event_item.y = max_y + y_off1
                    event_item.width = column_width - 4
                    event_item.height = y_off2
                    event_item.font_size = day.font_size
                    if event.start < event1_start and event.end > event1_end:
                        event_item.type = 'mid'
                    elif event.start < event1_start:
                        event_item.type = 'top'
                    elif event.end > event1_end:
                        event_item.type = 'bottom'
                    else:
                        event_item.type = 'topbottom'
                    event_item.update()

    def on_event_store_event_removed(self, store, event):
        self.update()

    def on_event_store_event_added(self, store, event):
        self.update()

    def on_key_press_event(self, widget, event):
        date = self.get_selected_date()
        if event.keyval == gtk.gdk.keyval_from_name('Up'):
            self.select(date - datetime.timedelta(7))
        elif event.keyval == gtk.gdk.keyval_from_name('Down'):
            self.select(date + datetime.timedelta(7))
        elif event.keyval == gtk.gdk.keyval_from_name('Left'):
            self.select(date - datetime.timedelta(1))
        elif event.keyval == gtk.gdk.keyval_from_name('Right'):
            self.select(date + datetime.timedelta(1))
        return True

    def on_event_item_button_press_event(self, item, rect, event):
        self.emit('event-clicked', item.event)

    def on_button_press_event(self, day, widget2, event):
        self.select(day.date)

gobject.signal_new('event-clicked',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('day-selected',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
