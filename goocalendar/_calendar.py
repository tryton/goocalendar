#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime
import calendar
import math
from operator import add

import gtk
import gobject
import goocanvas
import pango

import util
from .util import left_click


class Calendar(goocanvas.Canvas):
    AVAILABLE_VIEWS = ["month", "week"]
    MIN_PER_LEVEL = 15  # Number of minutes per graduation for drag and drop

    def __init__(self, event_store=None, view="month", time_format="%H:%M",
            firstweekday=calendar.SUNDAY):
        super(Calendar, self).__init__()
        self._selected_day = None
        self._bg_rect = None
        self._timeline = None
        self._line_height = 0
        self._realized = False
        self._event_store = None
        self._event_removed_sigid = None
        self._event_added_sigid = None
        self._events_cleared_sigid = None
        self.event_store = event_store
        self.firstweekday = firstweekday
        self._drag_start_date = None
        self._drag_date = None
        self._drag_x = None
        self._drag_y = None
        self._drag_height = 0
        self._last_click_x = None
        self._last_click_y = None
        self._last_click_time = 0
        self._day_width = 0
        self._day_height = 0
        self._event_items = []
        assert view in self.AVAILABLE_VIEWS
        self.view = view
        self.selected_date = datetime.date.today()
        self.time_format = time_format
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

        # Initialize background, timeline and days and add them to canvas
        root = self.get_root_item()
        style = self.get_style()
        color = util.color_to_string(style.bg[gtk.STATE_PRELIGHT])
        self._bg_rect = goocanvas.Rect(parent=root, x=0, y=0,
            stroke_color=color, fill_color=color)
        self._timeline = TimelineItem(self, time_format=self.time_format)
        root.add_child(self._timeline)
        self.days = []
        while len(self.days) < 42:  # 6 rows of 7 days
            box = DayItem(self)
            root.add_child(box)
            box.connect('button_press_event',
                self.on_day_item_button_press_event)
            self.days.append(box)

    def select(self, new_date):
        cal = calendar.Calendar(self.firstweekday)
        if hasattr(new_date, 'date'):
            new_date = new_date.date()
        old_date = self.selected_date
        old_day = self._selected_day
        self.selected_date = new_date
        page_changed = False
        if self.view == "month":
            page_changed = not util.same_month(old_date, new_date)
        elif self.view == "week":
            old_first_weekday = util.first_day_of_week(cal, old_date)
            new_first_weekday = util.first_day_of_week(cal, new_date)
            page_changed = old_first_weekday != new_first_weekday

        # This is slow: When the month was changed we need to update
        # the entire canvas.
        if old_day is None or page_changed:
            self.update()
            self.emit('day-selected', self.selected_date)
            self.emit('page-changed', self.selected_date)
            return

        # This is fast: Update only the old and newly selected days.
        # Find the canvas item that corresponds to the new date.
        weeks = cal.monthdayscalendar(new_date.year, new_date.month)
        found = -1
        for weekno, week in enumerate(weeks):
            for dayno, day in enumerate(week):
                if day == new_date.day:
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
        self._selected_day = new_day
        if old_day != new_day:
            self.emit('day-selected', self.selected_date)

    def previous_page(self):
        cal = calendar.Calendar(self.firstweekday)
        if self.view == "month":
            new_date = util.previous_month(cal, self.selected_date)
        elif self.view == "week":
            new_date = util.previous_week(cal, self.selected_date)
        self.select(new_date)

    def next_page(self):
        cal = calendar.Calendar(self.firstweekday)
        if self.view == "month":
            new_date = util.next_month(cal, self.selected_date)
        elif self.view == "week":
            new_date = util.next_month(cal, self.selected_date)
        self.select(new_date)

    def set_view(self, level):
        if level == self.view:
            return
        assert level in self.AVAILABLE_VIEWS
        self.view = level
        self.update()
        self.emit('view-changed', self.view)

    @property
    def event_store(self):
        return self._event_store

    @event_store.setter
    def event_store(self, event_store):
        # Disconnect previous event store if any
        if self._event_store:
            self._event_store.disconnect(self._event_removed_sigid)
            self._event_store.disconnect(self._event_added_sigid)
            self._event_store_disconnect(self._events_cleared_sigid)

        # Set and connect new event_store
        self._event_store = event_store
        self.update()
        if not event_store:
            return
        self._event_removed_sigid = self._event_store.connect('event-removed',
            self.on_event_store_event_removed)
        self._event_added_sigid = self._event_store.connect('event-added',
            self.on_event_store_event_added)
        self._events_cleared_sigid = \
            self._event_store.connect('events-cleared',
            self.on_event_store_events_cleared)

    def on_realize(self, *args):
        self._realized = True
        self.grab_focus(self.get_root_item())
        self.on_size_allocate(*args)

    def on_size_allocate(self, *args):
        alloc = self.get_allocation()
        if not self._realized or alloc.width < 10 or alloc.height < 10:
            return
        self.set_bounds(0, 0, alloc.width, alloc.height)
        self.update()

    def update(self):
        if not self._realized:
            return
        self.draw_background()
        if self.view == "month":
            self.draw_month()
        elif self.view == "week":
            self.draw_week()
        self.draw_events()

    def draw_background(self):
        x, y, w, h = self.get_bounds()
        self._bg_rect.set_property('width', w)
        self._bg_rect.set_property('height', h)

    def draw_week(self):
        """
        Draws the currently selected week.
        """
        style = self.get_style()
        pango_size = style.font_desc.get_size()
        text_color = util.color_to_string(style.fg[gtk.STATE_NORMAL])
        border_color = util.color_to_string(style.mid[gtk.STATE_NORMAL])
        body_color = util.color_to_string(style.light[gtk.STATE_ACTIVE])
        selected_border_color = util.color_to_string(
            style.mid[gtk.STATE_SELECTED])
        today_body_color = 'ivory'
        x, y, w, h = self.get_bounds()
        timeline_w = self._timeline.width
        caption_size = max(len(day_name) for day_name in calendar.day_name)
        caption_size += 3  # The needed space for the date before the day_name
        day_width_min = caption_size * pango_size / pango.SCALE
        day_width_max = (w - timeline_w) / 7
        self._day_width = max(day_width_min, day_width_max)
        self._day_height = h
        width, height = self.get_size_request()
        new_width = int(timeline_w + 7 * self._day_width)
        if (width != new_width and day_width_min >= day_width_max):
            self.set_size_request(new_width, height)  # Minimum widget size

        # Redraw all days.
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        for weekno, week in enumerate(weeks):
            # Hide all days that are not part of the current week.
            if self.selected_date not in week:
                for dayno, date in enumerate(week):
                    box = self.days[weekno * 7 + dayno]
                    box.set_property('visibility', goocanvas.ITEM_INVISIBLE)
                continue

            # Draw the days that are part of the current week.
            for dayno, current_date in enumerate(week):
                # Highlight the day according to it's selection.
                selected = current_date == self.selected_date
                if selected:
                    the_border_color = selected_border_color
                else:
                    the_border_color = border_color
                if current_date == datetime.date.today():
                    the_body_color = today_body_color
                else:
                    the_body_color = body_color

                # Draw.
                box = self.days[weekno * 7 + dayno]
                box.x = self._day_width * dayno + timeline_w
                box.y = 0
                box.width = self._day_width - 2
                box.height = self._day_height
                box.type = 'week'
                box.date = current_date
                box.full_border = selected
                box.border_color = the_border_color
                box.body_color = the_body_color
                box.title_text_color = text_color
                box.event_text_color = text_color
                box.set_property('visibility', goocanvas.ITEM_VISIBLE)
                box.update()

                if selected:
                    self._selected_day = box
                    self._line_height = self._selected_day.line_height

    def draw_month(self):
        """
        Draws the currently selected month.
        """
        style = self.get_style()
        x1, y1, w, h = self.get_bounds()
        pango_size = style.font_desc.get_size()
        caption_size = max(len(day_name) for day_name in calendar.day_name)
        caption_size += 3  # The needed space for the date before the day_name
        day_width_min = caption_size * pango_size / pango.SCALE
        day_width_max = w / 7
        self._day_width = max(day_width_min, day_width_max)
        self._day_height = h / 6
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
        if self._timeline is not None:
            self._timeline.set_property('visibility', goocanvas.ITEM_INVISIBLE)

        # Draw the grid.
        y_pos = 0
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        for weekno, week in enumerate(weeks):
            for dayno, date in enumerate(week):
                # The color depends on whether each day is part of the
                # current month.
                if (not util.same_month(date, self.selected_date)):
                    the_border_color = inactive_border_color
                    the_text_color = inactive_text_color
                else:
                    the_border_color = border_color
                    the_text_color = text_color

                # Highlight the day according to it's selection.
                selected = date == self.selected_date
                if selected:
                    the_border_color = selected_border_color
                if date == datetime.date.today():
                    the_body_color = today_body_color
                else:
                    the_body_color = body_color

                # Draw a box for the day.
                box = self.days[weekno * 7 + dayno]
                box.x = self._day_width * dayno
                box.y = y_pos
                box.width = self._day_width - 2
                box.height = self._day_height - 2
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
                    self._selected_day = box
                    self._line_height = self._selected_day.line_height

            y_pos += self._day_height

        width, height = self.get_size_request()
        new_width = int(7 * self._day_width)
        new_height = int(14 * box.line_height)
        if ((width != new_width and self._day_width == day_width_min)
            or new_height != height):
            self.set_size_request(new_width, new_height)

    def _get_day_item(self, find_date):
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, find_date)
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
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        start = event.start.date()
        end = event.end.date() if event.end else event.start.date()
        assert start <= end
        days = []
        for weekno, week in enumerate(weeks):
            if self.view == "week":
                if self.selected_date not in week:
                    continue
            for dayno, date in enumerate(week):
                if date >= start and date <= end:
                    days.append(self.days[weekno * 7 + dayno])
                if date == end:
                    return days
        if len(days) > 0:
            return days
        raise Exception('Days not found: %s %s' % (event.start, end))

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
        for item in self._event_items:
            self.get_root_item().remove_child(item)
        self._event_items = []
        for day in self.days:
            day.lines.clear()
            day.show_indic = False
            day.update()

        if not self._event_store:
            return

        cal = calendar.Calendar(self.firstweekday)
        if self.view == "month":
            weeks = util.my_monthdatescalendar(cal, self.selected_date)
            dates = []
            for week in weeks:
                dates += week
        else:
            dates = util.my_weekdatescalendar(cal, self.selected_date)

        # Retrieve a list of all events in the current time span,
        # and sort them by event length.
        onedaydelta = (datetime.timedelta(days=1)
            - datetime.timedelta(microseconds=1))
        start = datetime.datetime.combine(dates[0], datetime.time())
        end = datetime.datetime.combine(dates[-1], datetime.time()) \
            + onedaydelta
        events = self._event_store.get_events(start, end)
        events.sort(util.event_days, reverse=True)

        # Draw all-day events, longest event first.
        max_y = self._selected_day.line_height
        non_all_day_events = []
        for event in events:
            event.event_items = []
            # Handle non-all-day events differently in week mode.
            if (self.view == "week" and not event.all_day
                    and not event.multidays):
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
            all_day_events_height = (free_line + 2) * max_line_height
            all_day_events_height += (free_line + 1) * 2  # 2px margin per line
            all_day_events_height += 1  # 1px padding-top
            max_y = max(all_day_events_height, max_y)
            for day in days:
                day.lines[free_line] = 1

            # Split days into weeks.
            weeks = []
            week_start = 0
            week_end = 0
            while week_end < len(days):
                day = days[week_start]
                weekday = (day.date.weekday() - self.firstweekday) % 7
                week_end = week_start + (7 - weekday)
                week = days[week_start:week_end]
                weeks.append(week)
                week_start = week_end

            for week in weeks:
                dayno = 0
                day = week[dayno]
                event_item = EventItem(self, event=event,
                    time_format=self.time_format)
                if len(event.event_items):
                    event_item.no_caption = True
                event.event_items.append(event_item)
                event_item.connect('button_press_event',
                    self.on_event_item_button_press_event)
                event_item.connect('button_release_event',
                    self.on_event_item_button_release)
                event_item.connect('motion_notify_event',
                    self.on_event_item_motion_notified)
                self._event_items.append(event_item)
                self.get_root_item().add_child(event_item)
                event_item.x = day.x
                event_item.left_border = day.x + 2
                event_item.y = day.y + (free_line + 1) * day.line_height
                event_item.y += free_line * 2  # 2px of margin per line
                event_item.y += 1  # 1px padding-top
                event_item.width = (day.width + 2) * len(week)
                event_item.height = day.line_height
                week_start = week[0].date
                week_end = week[-1].date
                end = event.end if event.end else event.start
                if (event.start.date() < week_start
                        and end.date() > week_end):
                    event_item.type = 'mid'
                    event_item.width -= 3
                elif event.start.date() < week_start:
                    event_item.type = 'right'
                    event_item.width -= 4
                elif end.date() > week_end:
                    event_item.type = 'left'
                    event_item.x += 2
                    event_item.width -= 4
                else:
                    event_item.x += 2
                    event_item.width -= 6
                    event_item.type = 'leftright'
                event_item.update()

        if self.view != "week":
            return

        # Redraw the timeline.
        style = self.get_style()
        text_color = util.color_to_string(style.fg[gtk.STATE_NORMAL])
        border_color = util.color_to_string(style.mid[gtk.STATE_NORMAL])
        body_color = util.color_to_string(style.light[gtk.STATE_ACTIVE])
        self._timeline.set_property('visibility', goocanvas.ITEM_VISIBLE)
        x, y, w, h = self.get_bounds()
        self._timeline.x = x
        self._timeline.y = max_y
        self._timeline.height = h - max_y - 2
        self._timeline.line_color = body_color
        self._timeline.bg_color = border_color
        self._timeline.text_color = text_color
        self._timeline.update()
        width, height = self.get_size_request()
        min_line_height = self._timeline.min_line_height
        line_height = self._timeline.line_height
        self.minute_height = line_height / 60.0
        new_height = int(max_y + 24 * min_line_height)
        if (height != new_height):
            self.set_size_request(width, new_height)

        # Draw non-all-day events.
        for date in dates:
            date_start = datetime.datetime.combine(date, datetime.time())
            date_end = (datetime.datetime.combine(date_start, datetime.time())
                + datetime.timedelta(days=1))
            day = self._get_day_item(date)
            day_events = util.get_intersection_list(non_all_day_events,
                date_start, date_end)
            day_events.sort()
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

                    event_item = EventItem(self, event=event,
                        time_format=self.time_format)
                    if event.event_items:
                        event_item.no_caption = True
                    event.event_items.append(event_item)
                    event_item.connect('button_press_event',
                        self.on_event_item_button_press_event)
                    event_item.connect('button_release_event',
                        self.on_event_item_button_release)
                    event_item.connect('motion_notify_event',
                        self.on_event_item_motion_notified)
                    self._event_items.append(event_item)
                    self.get_root_item().add_child(event_item)
                    y_off1 = top_offset_mins * self.minute_height
                    y_off2 = bottom_offset_mins * self.minute_height
                    column_width = day.width / parallel
                    event_item.left_border = day.x + 2
                    event_item.x = day.x + (columnno * column_width) + 2
                    event_item.y = max_y + y_off1
                    event_item.width = column_width - 4
                    if columnno != (parallel - 1):
                        event_item.width += column_width / 1.2
                    event_item.height = y_off2
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

    def on_event_store_events_cleared(self, store):
        self.update()

    def on_key_press_event(self, widget, event):
        date = self.selected_date
        if event.keyval == gtk.gdk.keyval_from_name('Up'):
            self.select(date - datetime.timedelta(7))
        elif event.keyval == gtk.gdk.keyval_from_name('Down'):
            self.select(date + datetime.timedelta(7))
        elif event.keyval == gtk.gdk.keyval_from_name('Left'):
            self.select(date - datetime.timedelta(1))
        elif event.keyval == gtk.gdk.keyval_from_name('Right'):
            self.select(date + datetime.timedelta(1))

    @left_click
    def on_day_item_button_press_event(self, day, widget2, event):
        self.emit('day-pressed', day.date)
        self.select(day.date)

        if self._is_double_click(event):
            self.emit('day-activated', day.date)

    def _is_double_click(self, event):
        gtk_settings = gtk.settings_get_default()
        double_click_distance = gtk_settings.props.gtk_double_click_distance
        double_click_time = gtk_settings.props.gtk_double_click_time
        if (self._last_click_x is not None and
                event.time < (self._last_click_time + double_click_time) and
                abs(event.x - self._last_click_x) <= double_click_distance and
                abs(event.y - self._last_click_y) <= double_click_distance):
            self._last_click_x = None
            self._last_click_y = None
            self._last_click_time = None
            return True
        else:
            self._last_click_x = event.x
            self._last_click_y = event.y
            self._last_click_time = event.time
            return False

    def get_cur_pointed_date(self, x, y):
        """
        Return the date of the day_item pointed by two coordinates [x,y]
        """
        # Get current week
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        if self.view == 'week':
            cur_week, = (week for week in weeks for date in week
                if self.selected_date == date)
        elif self.view == 'month':
            max_height = 6 * self._day_height
            if y < 0:
                weekno = 0
            elif y > max_height:
                weekno = 5
            else:
                weekno = int(y / self._day_height)
            cur_week = weeks[weekno]

        # Get Current pointed date
        max_width = 7 * self._day_width
        if x < 0:
            day_no = 0
        elif x > max_width:
            day_no = 6
        else:
            offset_x = self._timeline.width if self.view == 'week' else 0
            day_no = int((x - offset_x) / self._day_width)
        return cur_week[day_no]

    @left_click
    def on_event_item_button_press_event(self, event_item, rect, event):

        # Drag and drop starting coordinates
        self._drag_x = event.x
        self._drag_y = event.y
        self._drag_height = 0
        self._drag_start_date = self.get_cur_pointed_date(event.x, event.y)
        self._drag_date = self._drag_start_date
        self.set_has_tooltip(False)
        event_item.raise_(None)
        event_item.transparent = True

        event_item.width = self._day_width - 6  # Biggest event width
        event_date = event_item.event.start.date()
        daysdelta = self._drag_start_date - event_date
        if self.view == 'week':
            event_item.x = event_item.left_border
            if ((event_item.event.all_day or event_item.event.multidays)
                and self._drag_start_date != event_date):
                event_item.x += daysdelta.days * self._day_width
                event_item.event.start += daysdelta
                if event_item.event.end:
                    event_item.event.end += daysdelta
            else:
                for item in event_item.event.event_items:
                    if item != event_item:
                        self.get_root_item().remove_child(item)
                        self._event_items.remove(item)

                event_item.height = 2 * self._line_height
                day_no = (int((event.x - self._timeline.width)
                    / self._day_width))
                day_off = day_no * self._day_width + 2
                event_item.x = self._timeline.width + day_off
                if (event_item.no_caption or event.y < event_item.y or
                    event.y > (event_item.y + event_item.height)):
                    # click was not performed inside the new day item
                    level_height = self.minute_height * self.MIN_PER_LEVEL
                    cur_level = int((event.y - self._timeline.y)
                        / level_height)
                    nb_levels_per_hour = 60 / self.MIN_PER_LEVEL
                    cur_level -= nb_levels_per_hour  # click is in the middle
                    if cur_level < 0:
                        cur_level = 0
                    event_item.y = self._timeline.y + cur_level * level_height
                    nb_minutes = cur_level * self.MIN_PER_LEVEL
                    minutes = nb_minutes % 60
                    hours = nb_minutes / 60
                    old_start = event_item.event.start
                    new_start = \
                        datetime.datetime.combine(self._drag_start_date,
                        datetime.time(hours, minutes))
                    event_item.event.start = new_start
                    delta = new_start - old_start
                    if event_item.event.end:
                        event_item.event.end += delta
                event_item.no_caption = False
        elif self.view == 'month':
            for item in event_item.event.event_items:
                if item != event_item:
                    self.get_root_item().remove_child(item)
                    self._event_items.remove(item)
                else:
                    event_item.event.start += daysdelta
                    if event_item.event.end:
                        event_item.event.end += daysdelta
                    weekno = int(event.y / self._day_height)
                    day_no = int(event.x / self._day_width)
                    event_item.y = weekno * self._day_height
                    event_item.y += int(self._line_height) + 1  # padding-top
                    event_item.x = day_no * self._day_width + 2  # padding-left
                    item_height = self._line_height + 2  # 2px between items
                    while event_item.y < event.y:
                        event_item.y += item_height
                    event_item.y -= item_height
                    event_item.no_caption = False
        event_item.update()
        self.emit('event-pressed', event_item.event)

        if self._is_double_click(event):
            self._stop_drag_and_drop()
            self.emit('event-activated', event_item.event)

    def on_event_item_button_release(self, event_item, rect, event):
        event_item.transparent = False
        self._stop_drag_and_drop()
        self.draw_events()
        self.emit('event-released', event_item.event)

    def _stop_drag_and_drop(self):
        self._drag_x = None
        self._drag_y = None
        self._drag_height = 0
        self._drag_start_date = None
        self._drag_date = None
        self.set_has_tooltip(True)

    def on_event_item_motion_notified(self, event_item, rect, event):
        if self._drag_x and self._drag_y:
            # We are currently drag and dropping this event item
            diff_y = event.y - self._drag_y
            self._drag_x = event.x
            self._drag_y = event.y
            self._drag_height += diff_y

            cur_pointed_date = self.get_cur_pointed_date(event.x, event.y)
            daysdelta = cur_pointed_date - self._drag_date
            if self.view == 'month':
                if cur_pointed_date != self._drag_date:
                    event_item.event.start += daysdelta
                    if event_item.event.end:
                        event_item.event.end += daysdelta
                    nb_lines = int(round(float(daysdelta.days) / 7))
                    nb_columns = daysdelta.days - nb_lines * 7
                    event_item.x += nb_columns * self._day_width
                    self._drag_date = cur_pointed_date
                event_item.y += diff_y
                event_item.update()
                return

            # Handle horizontal translation
            if cur_pointed_date != self._drag_date:
                self._drag_date = cur_pointed_date
                event_item.event.start += daysdelta
                if event_item.event.end:
                    event_item.event.end += daysdelta
                event_item.x += daysdelta.days * self._day_width

            if event_item.event.multidays or event_item.event.all_day:
                event_item.update()
                return

            # Compute vertical translation
            diff_minutes = int(round(self._drag_height / self.minute_height))
            diff_time = datetime.timedelta(minutes=diff_minutes)
            old_start = event_item.event.start
            new_start = old_start + diff_time
            next_level = util.next_level(old_start, self.MIN_PER_LEVEL)
            prev_level = util.prev_level(old_start, self.MIN_PER_LEVEL)
            if diff_time >= datetime.timedelta(0) and new_start >= next_level:
                new_start = util.prev_level(new_start, self.MIN_PER_LEVEL)
            elif diff_time < datetime.timedelta(0) and new_start <= prev_level:
                new_start = util.next_level(new_start, self.MIN_PER_LEVEL)
            else:
                # We stay at the same level
                event_item.update()
                return

            # Apply vertical translation
            midnight = datetime.time()
            old_start_midnight = datetime.datetime.combine(old_start, midnight)
            onedaydelta = datetime.timedelta(days=1)
            next_day_midnight = old_start_midnight + onedaydelta
            if new_start.day < old_start.day:
                new_start = old_start_midnight
            elif new_start >= next_day_midnight:
                seconds_per_level = 60 * self.MIN_PER_LEVEL
                level_delta = datetime.timedelta(seconds=seconds_per_level)
                last_level = next_day_midnight - level_delta
                new_start = last_level
            event_item.event.start = new_start
            if event_item.event.end:
                timedelta = new_start - old_start
                event_item.event.end += timedelta
            pxdelta = (timedelta.total_seconds() / 60 * self.minute_height)
            event_item.y += pxdelta
            event_item.update()
            self._drag_height -= pxdelta

gobject.signal_new('event-pressed',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('event-activated',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('event-released',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('day-pressed',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('day-activated',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('day-selected',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('view-changed',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))
gobject.signal_new('page-changed',
    Calendar,
    gobject.SIGNAL_RUN_FIRST,
    gobject.TYPE_NONE,
    (gobject.TYPE_PYOBJECT,))


class DayItem(goocanvas.Group):
    """
    A canvas item representing a day.
    """

    def __init__(self, cal, **kwargs):
        super(DayItem, self).__init__()

        self._cal = cal
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

        week_day = self.date.weekday()
        day_name = calendar.day_name[week_day]
        caption = '%s %s' % (self.date.day, day_name)
        style = self._cal.get_style()
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


class EventItem(goocanvas.Group):
    """
    A canvas item representing an event.
    """

    def __init__(self, cal, **kwargs):
        super(EventItem, self).__init__()

        self._cal = cal
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.width = kwargs.get('width')
        self.height = kwargs.get('height')
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color')
        self.event = kwargs.get('event')
        self.type = kwargs.get('type', 'leftright')
        self.time_format = kwargs.get('time_format')
        self.transparent = False
        self.no_caption = False

        # Create canvas items.
        self.box = goocanvas.Rect(parent=self)
        self.text = goocanvas.Text(parent=self)
        style = self._cal.get_style()
        font_descr = style.font_desc.copy()
        self.font = font_descr.to_string()
        self.text.set_property('font', self.font)
        logical_height = self.text.get_natural_extents()[1][3]
        self.line_height = logical_height / pango.SCALE

        if self.x is not None:
            self.update()

    def update(self):
        if (self.event.all_day or self._cal.view == "month"
                or self.event.multidays):
            self.update_all_day_event()
        else:
            self.update_event()

    def update_event(self):
        self.width = max(self.width, 0)
        starttime = self.event.start.strftime(self.time_format)
        endtime = self.event.end.strftime(self.time_format)
        tooltip = '%s - %s\n%s' % (starttime, endtime, self.event.caption)

        # Do we have enough width for caption
        first_line = starttime + ' - ' + endtime
        self.text.set_property('text', first_line)
        logical_width = self.text.get_natural_extents()[1][2] / pango.SCALE
        if self.width < logical_width:
            first_line = starttime + ' - '

        second_line = self.event.caption
        self.text.set_property('text', second_line)
        logical_width = self.text.get_natural_extents()[1][2] / pango.SCALE
        if self.width < logical_width:
            second_line = None

        # Do we have enough height for whole caption
        if self.height >= (2 * self.line_height):
            caption = first_line
            if second_line:
                caption += '\n' + second_line
        elif self.height >= self.line_height:
            caption = first_line
        else:
            caption = ''
        caption = '' if self.no_caption else caption
        the_event_bg_color = self.event.bg_color

        # Choose text color.
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        if the_event_bg_color is not None:
            self.box.set_property('x', self.x)
            self.box.set_property('y', self.y)
            self.box.set_property('width', self.width)
            self.box.set_property('height', self.height)
            self.box.set_property('stroke_color', the_event_bg_color)
            bg_rgba_color = self.box.get_property('stroke_color_rgba')
            bg_colors = list(util.rgba_to_colors(bg_rgba_color))
            # We make background color 1/4 brighter (+64 over 255)
            bg_colors[:3] = map(min,
                map(add, bg_colors[:3], (64,) * 3), (255,) * 3)
            bg_colors = util.colors_to_rgba(*bg_colors)
            self.box.set_property('fill_color_rgba', bg_colors)

            # Alpha color is set to half of 255, i.e an opacity of 5O percents
            transparent_color = self.box.get_property('fill_color_rgba') - 128
            if self.transparent:
                self.box.set_property('stroke_color_rgba', transparent_color)
                self.box.set_property('fill_color_rgba', transparent_color)
            self.box.set_property('tooltip', tooltip)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('text', caption)
        self.text.set_property('fill_color', the_event_text_color)
        self.text.set_property('tooltip', tooltip)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (self.x, self.y, self.x, y2,
            x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)

    def update_all_day_event(self):
        self.width = max(self.width, 0)
        startdate = self.event.start.strftime('%x')
        starttime = self.event.start.strftime(self.time_format)
        if self.event.end:
            enddate = self.event.end.strftime('%x')
            endtime = self.event.end.strftime(self.time_format)

        if self.event.all_day:
            caption = self.event.caption
            if not self.event.end:
                tooltip = '%s\n%s' % (startdate, caption)
            else:
                tooltip = '%s - %s\n%s' % (startdate, enddate, caption)
        elif self.event.multidays:
            caption = '%s %s' % (starttime, self.event.caption)
            tooltip = '%s %s - %s %s\n%s' % (startdate, starttime, enddate,
                endtime, self.event.caption)
        else:
            caption = '%s %s' % (starttime, self.event.caption)
            tooltip = '%s - %s\n%s' % (starttime, endtime, self.event.caption)
        caption = '' if self.no_caption else caption
        the_event_bg_color = self.event.bg_color
        self.text.set_property('text', caption)
        logical_height = self.text.get_natural_extents()[1][3]
        self.height = logical_height / pango.SCALE

        # Choose text color.
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        if the_event_bg_color is not None:
            self.box.set_property('x', self.x)
            self.box.set_property('y', self.y)
            self.box.set_property('width', self.width)
            self.box.set_property('height', self.height)
            self.box.set_property('stroke_color', the_event_bg_color)
            bg_rgba_color = self.box.get_property('stroke_color_rgba')
            bg_colors = list(util.rgba_to_colors(bg_rgba_color))
            bg_colors[:3] = map(min,
                map(add, bg_colors[:3], (64,) * 3), (255,) * 3)
            bg_colors = util.colors_to_rgba(*bg_colors)
            self.box.set_property('fill_color_rgba', bg_colors)
            transparent_color = self.box.get_property('fill_color_rgba') - 128
            if self.transparent:
                self.box.set_property('stroke_color_rgba', transparent_color)
                self.box.set_property('fill_color_rgba', transparent_color)
            self.box.set_property('tooltip', tooltip)

        # Print the event name into the title box.
        self.text.set_property('x', self.x + 2)
        self.text.set_property('y', self.y)
        self.text.set_property('fill_color', the_event_text_color)
        self.text.set_property('tooltip', tooltip)

        # Clip the text.
        x2, y2 = self.x + self.width, self.y + self.height,
        path = 'M%s,%s L%s,%s L%s,%s L%s,%s Z' % (
            self.x, self.y, self.x, y2, x2, y2, x2, self.y)
        self.text.set_property('clip_path', path)


class TimelineItem(goocanvas.Group):
    """
    A canvas item representing a timeline.
    """

    def __init__(self, cal, **kwargs):
        super(TimelineItem, self).__init__()

        self._cal = cal
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.line_color = kwargs.get('line_color')
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color')
        self.time_format = kwargs.get('time_format')
        self.width = 0

        # Create canvas items.
        self._timeline_rect = {}
        self._timeline_text = {}
        for n in range(24):
            caption = datetime.time(n).strftime(self.time_format)
            self._timeline_rect[n] = goocanvas.Rect(parent=self)
            self._timeline_text[n] = goocanvas.Text(parent=self, text=caption)

        if self.x is not None:
            self.update()

    @property
    def min_line_height(self):
        logical_height = 0
        self.ink_padding_top = 0
        for n in range(24):
            natural_extents = self._timeline_text[n].get_natural_extents()
            logical_rect = natural_extents[1]
            logical_height = max(logical_height, logical_rect[3])
            ink_rect = natural_extents[0]
            self.ink_padding_top = max(self.ink_padding_top, ink_rect[0])
        line_height = int(math.ceil(float(logical_height) / pango.SCALE))
        return line_height

    @property
    def line_height(self):
        self.padding_top = 0
        line_height = self.min_line_height
        if line_height < self.height / 24:
            line_height = self.height / 24
            pango_size = self._cal.get_style().font_desc.get_size()
            padding_top = (line_height - pango_size / pango.SCALE) / 2
            padding_top -= int(math.ceil(float(self.ink_padding_top) /
                pango.SCALE))
            self.padding_top = padding_top
        return line_height

    def _compute_width(self):
        style = self._cal.get_style()
        font = style.font_desc
        ink_padding_left = 0
        ink_max_width = 0
        for n in range(24):
            self._timeline_text[n].set_property('font', font)
            natural_extents = self._timeline_text[n].get_natural_extents()
            ink_rect = natural_extents[0]
            ink_padding_left = max(ink_padding_left, ink_rect[0])
            ink_max_width = max(ink_max_width, ink_rect[2])
        self.width = int(math.ceil(float(ink_padding_left + ink_max_width)
            / pango.SCALE))

    def update(self):
        self._compute_width()
        line_height = self.line_height

        # Draw the timeline.
        for n in range(24):
            rect = self._timeline_rect[n]
            text = self._timeline_text[n]
            y = self.y + n * line_height

            rect.set_property('x', self.x)
            rect.set_property('y', y)
            rect.set_property('width', self.width)
            rect.set_property('height', line_height)
            rect.set_property('stroke_color', self.line_color)
            rect.set_property('fill_color', self.bg_color)

            text.set_property('x', self.x)
            text.set_property('y', y + self.padding_top)
            text.set_property('fill_color', self.text_color)
