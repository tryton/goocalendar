# This file is part of GooCalendar.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import calendar
import datetime

from gi.repository import Gdk, GObject, Gtk, Pango, PangoCairo

from . import util


class Calendar(Gtk.DrawingArea):
    AVAILABLE_VIEWS = ["month", "week", "day"]
    MIN_PER_LEVEL = 15  # Number of minutes per graduation for drag and drop

    __gproperties__ = {
        'text-color': (GObject.TYPE_STRING, '#2E3634', "Text Color",
            "The color of the text", GObject.ParamFlags.READWRITE),
        'selected-text-color': (GObject.TYPE_STRING, '#2E3634', "Text Color",
            "Selected color of the text", GObject.ParamFlags.READWRITE),
        'inactive-text-color': (GObject.TYPE_STRING, '#8B8F8E',
            "Inactive Text Color", "The color of the inactive text",
            GObject.ParamFlags.READWRITE),
        'border-color': (GObject.TYPE_STRING, '#D2D0D2', "Border Color",
            "The color of border", GObject.ParamFlags.READWRITE),
        'selected-border-color': (GObject.TYPE_STRING, '#5EC590',
            "Selected Border Color", "The color of selected border",
            GObject.ParamFlags.READWRITE),
        'inactive-border-color': (GObject.TYPE_STRING, '#E8E7E8',
            "Inactive Border Color", "The color of inactive border",
            GObject.ParamFlags.READWRITE),
        'body-color': (GObject.TYPE_STRING, 'white', "Body Color",
            "The color of the body", GObject.ParamFlags.READWRITE),
        'today-body-color': (GObject.TYPE_STRING, 'ivory', "Today Body Color",
            "The color of the today body", GObject.ParamFlags.READWRITE),
        'font': (GObject.TYPE_STRING, '', "Font",
            "The attributes specifying which font to use",
            GObject.ParamFlags.READWRITE),
        }

    def __init__(self, event_store=None, view="month", time_format="%H:%M",
            firstweekday=calendar.SUNDAY):
        super(Calendar, self).__init__()
        settings = Gtk.Settings.get_default()
        self.__props = {
            'text-color': '#2E3634',
            'selected-text-color': '#2E3634',
            'inactive-text-color': '#8B8F8E',
            'border-color': '#D2D0D2',
            'selected-border-color': '#5EC590',
            'inactive-border-color': '#E8E7E8',
            'body-color': 'white',
            'today-body-color': 'ivory',
            'font': settings.get_property('gtk-font-name'),
            }
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
        self._tooltip_text = None
        self._tooltip_x = None
        self._tooltip_y = None
        assert view in self.AVAILABLE_VIEWS
        self.view = view
        self.selected_date = datetime.date.today()
        self.time_format = time_format
        self.min_width = self.min_height = 200
        self.set_can_focus(True)
        self.add_events(
            Gdk.EventMask.EXPOSURE_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_HINT_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
            | Gdk.EventMask.KEY_RELEASE_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.FOCUS_CHANGE_MASK)
        self.connect('realize', self.on_realize)
        self.connect('size-allocate', self.on_size_allocate)
        self.connect('key-press-event', self.on_key_press_event)
        self.connect('draw', self.on_draw)
        self.connect('button-press-event', self.on_button_press_event)
        self.connect('button-release-event', self.on_button_release_event)
        self.connect('motion-notify-event', self.on_motion_notify_event)
        self.connect('query-tooltip', self.on_query_tooltip)

        # Initialize day and event data structures
        self.days = []
        while len(self.days) < 42:  # 6 rows of 7 days
            box = DayItem(self)
            self.days.append(box)

        self._timeline = TimelineItem(self, time_format=self.time_format)

    def do_set_property(self, prop, value):
        self.__props[prop.name] = value

    def do_get_property(self, prop):
        return self.__props[prop.name]

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_height(self):
        return self.min_height, int(self.min_height * 1.5)

    def do_get_preferred_width(self):
        return self.min_width, int(self.min_width * 1.5)

    @property
    def font_size(self):
        return self.get_style_context().get_property(
            'font', Gtk.StateFlags.NORMAL).get_size()

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
            page_changed = (
                old_first_weekday != new_first_weekday
                or old_date.month != new_date.month)
        elif self.view == "day":
            page_changed = old_date != new_date

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
        old_title_text_color = old_day.title_text_color
        old_day.full_border = False
        old_day.border_color = new_day.border_color
        old_day.title_text_color = new_day.title_text_color
        new_day.border_color = old_border_color
        new_day.title_text_color = old_title_text_color
        new_day.full_border = True

        # Redraw.
        self._selected_day = new_day
        if old_day != new_day:
            self.emit('day-selected', self.selected_date)
        self.queue_draw()

    def previous_page(self):
        cal = calendar.Calendar(self.firstweekday)
        new_date = getattr(
            util, 'previous_%s' % self.view)(cal, self.selected_date)
        self.select(new_date)

    def next_page(self):
        cal = calendar.Calendar(self.firstweekday)
        new_date = getattr(
            util, 'next_%s' % self.view)(cal, self.selected_date)
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
            self._event_store.disconnect(self._events_cleared_sigid)

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
        self.grab_focus()
        self.on_size_allocate(*args)

    def on_size_allocate(self, *args):
        alloc = self.get_allocation()
        if not self._realized or alloc.width < 10 or alloc.height < 10:
            return
        self.update()

    def update(self):
        if not self._realized:
            return
        min_size = (self.min_width, self.min_height)
        self._prepare_layout()
        if min_size != (self.min_width, self.min_height):
            self.queue_resize()
        self.queue_draw()

    def _prepare_layout(self):
        """Prepare the layout data for drawing."""
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        if self.view == "month":
            self._prepare_month_layout(w, h)
        elif self.view == "week":
            self._prepare_week_layout(w, h)
        elif self.view == "day":
            self._prepare_day_layout(w, h)
        self._prepare_events()

    def _prepare_day_layout(self, w, h):
        """
        Prepares the layout for the currently selected day.
        """
        timeline_w = self._timeline.get_width(self)
        dayno = self.selected_date.weekday()
        day_name = calendar.day_name[dayno]
        caption_size = len(day_name) + 3
        day_width_min = caption_size * self.font_size / Pango.SCALE
        day_width_max = (w - timeline_w)
        self._day_width = max(day_width_min, day_width_max)
        self._day_height = h

        # Prepare all days.
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        for weekno, week in enumerate(weeks):
            for i, date in enumerate(week):
                box = self.days[weekno * 7 + i]
                box.visible = False
            if self.selected_date not in week:
                continue

            if self.selected_date == datetime.date.today():
                the_body_color = self.props.today_body_color
            else:
                the_body_color = self.props.body_color

            box = self.days[weekno * 7 + dayno]
            box.x = timeline_w
            box.y = 0
            box.width = self._day_width - 2
            box.height = self._day_height
            box.type = 'day'
            box.date = self.selected_date
            box.full_border = True
            box.border_color = self.props.selected_border_color
            box.body_color = the_body_color
            box.title_text_color = self.props.selected_text_color
            box.visible = True

        self.min_width = int(timeline_w + day_width_min)
        self.min_height = int(
            (24 + 1) * self._timeline.get_min_line_height(self))

    def _prepare_week_layout(self, w, h):
        """
        Prepares the layout for the currently selected week.
        """
        timeline_w = self._timeline.get_width(self)
        caption_size = max(len(day_name) for day_name in calendar.day_name)
        caption_size += 3  # The needed space for the date before the day_name
        day_width_min = caption_size * self.font_size / Pango.SCALE
        day_width_max = (w - timeline_w) / 7
        self._day_width = max(day_width_min, day_width_max)
        self._day_height = h

        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        for weekno, week in enumerate(weeks):
            if self.selected_date not in week:
                for dayno, date in enumerate(week):
                    box = self.days[weekno * 7 + dayno]
                    box.visible = False
                continue

            for dayno, current_date in enumerate(week):
                selected = current_date == self.selected_date
                if selected:
                    the_border_color = self.props.selected_border_color
                    the_text_color = self.props.selected_text_color
                else:
                    the_border_color = self.props.border_color
                    the_text_color = self.props.text_color
                if current_date == datetime.date.today():
                    the_body_color = self.props.today_body_color
                else:
                    the_body_color = self.props.body_color

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
                box.title_text_color = the_text_color
                box.visible = True

                if selected:
                    self._selected_day = box

        self.min_width = int(timeline_w + 7 * day_width_min)
        self.min_height = int(
            (24 + 1) * self._timeline.get_min_line_height(self))

    def _prepare_month_layout(self, w, h):
        """
        Prepares the layout for the currently selected month.
        """
        caption_size = max(len(day_name) for day_name in calendar.day_name)
        caption_size += 3  # The needed space for the date before the day_name
        day_width_min = caption_size * self.font_size / Pango.SCALE
        day_width_max = w / 7
        self._day_width = max(day_width_min, day_width_max)
        self._day_height = h / 6

        y_pos = 0
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
        for weekno, week in enumerate(weeks):
            for dayno, date in enumerate(week):
                if (not util.same_month(date, self.selected_date)):
                    the_border_color = self.props.inactive_border_color
                    the_text_color = self.props.inactive_text_color
                else:
                    the_border_color = self.props.border_color
                    the_text_color = self.props.text_color

                selected = date == self.selected_date
                if selected:
                    the_border_color = self.props.selected_border_color
                    the_text_color = self.props.selected_text_color
                if date == datetime.date.today():
                    the_body_color = self.props.today_body_color
                else:
                    the_body_color = self.props.body_color

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
                box.type = 'month'
                box.visible = True

                if selected:
                    self._selected_day = box

            y_pos += self._day_height

        self.min_width = int(7 * day_width_min)
        self.min_height = int(
            (6 * 2 + 1) * self._timeline.get_min_line_height(self))

    def _get_day_item(self, find_date):
        cal = calendar.Calendar(self.firstweekday)
        weeks = util.my_monthdatescalendar(cal, self.selected_date)
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

    def _find_free_line(self, days, n_lines):
        for line in range(n_lines):
            free = True
            for day in days:
                if line in day.lines:
                    free = False
                    break
            if free:
                return line
        return None

    def _prepare_events(self):
        alloc = self.get_allocation()
        bound_width = alloc.width

        # Clear previous events.
        self._event_items = []
        for day in self.days:
            day.lines.clear()
            day.show_indic = False
            # Compute line height for each visible day
            if day.visible:
                day.compute_line_height(self)

        if not self._event_store:
            return

        cal = calendar.Calendar(self.firstweekday)
        if self.view == "month":
            weeks = util.my_monthdatescalendar(cal, self.selected_date)
            dates = []
            for week in weeks:
                dates += week
        elif self.view == "week":
            dates = util.my_weekdatescalendar(cal, self.selected_date)
        else:
            dates = [self.selected_date]

        # Retrieve a list of all events in the current time span,
        # and sort them by event length.
        onedaydelta = (datetime.timedelta(days=1)
            - datetime.timedelta(microseconds=1))
        start = datetime.datetime.combine(dates[0], datetime.time())
        end = datetime.datetime.combine(dates[-1], datetime.time()) \
            + onedaydelta
        events = self._event_store.get_events(start, end)
        events.sort(key=util.event_days, reverse=True)

        # Draw all-day events, longest event first.
        max_y = 0
        non_all_day_events = []
        for event in events:
            event.event_items = []
            if (self.view in {"week", "day"} and not event.all_day
                    and not event.multidays):
                non_all_day_events.append(event)
                continue

            # Find a line that is free in all of the days.
            days = self._get_day_items(event)
            n_lines = days[0].n_lines
            if self.view in {"week", "day"}:
                n_lines = min(n_lines // 2, max(n_lines - 24, 0))
            free_line = self._find_free_line(days, n_lines)
            if free_line is None:
                for day in days:
                    day.show_indic = True
                continue

            max_line_height = max(x.line_height for x in days)
            all_day_events_height = (free_line + 2) * max_line_height
            all_day_events_height += (free_line + 1) * 2  # 2px margin per line
            all_day_events_height += 1  # 1px padding-top
            max_y = max(all_day_events_height, max_y)
            for day in days:
                for i in range(free_line,
                        free_line + len(event.caption.splitlines())):
                    day.lines[i] = 1

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
                self._event_items.append(event_item)
                if self.view == "day":
                    x_start = self._timeline.get_width(self)
                    width = bound_width - self._timeline.get_width(self)
                else:
                    x_start = day.x
                    width = (day.width + 2) * len(week)
                event_item.x = x_start
                event_item.left_border = x_start + 2
                event_item.y = day.y + (free_line + 1) * day.line_height
                event_item.y += free_line * 2  # 2px of margin per line
                event_item.y += 1  # 1px padding-top
                event_item.width = width
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

        # Add the day title
        if self._selected_day:
            max_y += self._selected_day.line_height
            self._line_height = self._selected_day.line_height

        if self.view == "month":
            return

        # Prepare the timeline.
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height
        max_y += (h - max_y) % 24
        self._timeline.x = 0
        self._timeline.y = max_y
        self._timeline.height = h - max_y
        self._timeline.line_color = self.props.body_color
        self._timeline.bg_color = self.props.border_color
        self._timeline.text_color = self.props.text_color
        self._timeline.visible = True

        min_line_height = self._timeline.get_min_line_height(self)
        line_height = self._timeline.get_line_height(self)
        self.minute_height = line_height / 60.0
        self.min_height = int(max_y + 24 * min_line_height)

        # Prepare non-all-day events.
        for date in dates:
            date_start = datetime.datetime.combine(date, datetime.time())
            date_end = (datetime.datetime.combine(date_start, datetime.time())
                + datetime.timedelta(days=1))
            day = self._get_day_item(date)
            day_events = util.get_intersection_list(non_all_day_events,
                date_start, date_end)
            day_events.sort()
            columns = []

            remaining_events = day_events[:]
            while len(remaining_events) > 0:
                columns.append([remaining_events[0]])
                for event in remaining_events[1:]:
                    intersections = util.count_intersections(columns[-1],
                        event.start, event.end)
                    if intersections == 0:
                        columns[-1].append(event)
                for event in columns[-1]:
                    remaining_events.remove(event)

            for columnno, column in enumerate(columns):
                for event in column:
                    event1_start = max(event.start, date_start)
                    event1_end = min(event.end, date_end)

                    parallel = util.count_parallel_events(day_events,
                        event1_start, event1_end)

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
                    self._event_items.append(event_item)
                    y_off1 = top_offset_mins * self.minute_height
                    y_off2 = bottom_offset_mins * self.minute_height
                    if self.view == "day":
                        x_start = self._timeline.get_width(self)
                        column_width = (
                            (w - self._timeline.get_width(self)) / parallel)
                    else:
                        column_width = day.width / parallel
                        x_start = day.x
                    event_item.left_border = x_start + 2
                    event_item.x = x_start + (columnno * column_width) + 2
                    event_item.y = max_y + y_off1
                    event_item.width = column_width - 4
                    if columnno != (parallel - 1):
                        event_item.width += column_width / 1.2
                    event_item.height = max(
                        event_item.get_line_height(self), y_off2)
                    if event.start < event1_start and event.end > event1_end:
                        event_item.type = 'mid'
                    elif event.start < event1_start:
                        event_item.type = 'top'
                    elif event.end > event1_end:
                        event_item.type = 'bottom'
                    else:
                        event_item.type = 'topbottom'

    def on_draw(self, widget, cr):
        """Handle the draw signal - draw the entire calendar."""
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Draw background
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Draw all visible day items
        for day in self.days:
            if day.visible:
                day.draw(cr, self)

        # Draw timeline for week/day views
        if self.view in ("week", "day") and self._timeline.visible:
            self._timeline.draw(cr, self)

        # Draw all event items
        for event_item in self._event_items:
            event_item.draw(cr, self)

        return False

    def on_event_store_event_removed(self, store, event):
        self.update()

    def on_event_store_event_added(self, store, event):
        self.update()

    def on_event_store_events_cleared(self, store):
        self.update()

    def on_key_press_event(self, widget, event):
        date = self.selected_date
        if event.keyval == Gdk.KEY_Up:
            self.select(date - datetime.timedelta(7))
        elif event.keyval == Gdk.KEY_Down:
            self.select(date + datetime.timedelta(7))
        elif event.keyval == Gdk.KEY_Left:
            self.select(date - datetime.timedelta(1))
        elif event.keyval == Gdk.KEY_Right:
            self.select(date + datetime.timedelta(1))

    def on_button_press_event(self, widget, event):
        if event.button != 1:
            return False

        x, y = event.x, event.y

        # Check if an event item was clicked
        for event_item in reversed(self._event_items):
            if event_item.contains_point(x, y):
                self._handle_event_item_press(event_item, event)
                return True

        # Check if a day was clicked
        for day in self.days:
            if day.visible and day.contains_point(x, y):
                self._handle_day_press(day, event)
                return True

        return False

    def on_button_release_event(self, widget, event):
        # Find if we're releasing on an event item
        for event_item in self._event_items:
            if event_item.contains_point(event.x, event.y):
                if self._drag_x is not None:
                    event_item.transparent = False
                    self._stop_drag_and_drop()
                    self.update()
                    self.emit('event-released', event_item.event)
                    return True
        if self._drag_x is not None:
            self._stop_drag_and_drop()
            self.update()
        return False

    def on_motion_notify_event(self, widget, event):
        if self._drag_x is None or self._drag_y is None:
            return False

        # Find the event item being dragged
        for event_item in self._event_items:
            if event_item.transparent:
                self._handle_event_item_motion(event_item, event)
                return True
        return False

    def on_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        # Check event items for tooltips
        for event_item in reversed(self._event_items):
            if event_item.contains_point(x, y):
                tooltip_text = event_item.get_tooltip()
                if tooltip_text:
                    tooltip.set_text(tooltip_text)
                    return True
        return False

    def _handle_day_press(self, day, event):
        self.emit('day-pressed', day.date)
        self.select(day.date)

        if self._is_double_click(event):
            self.emit('day-activated', day.date)

    def _is_double_click(self, event):
        gtk_settings = Gtk.Settings.get_default()
        double_click_distance = gtk_settings.props.gtk_double_click_distance
        double_click_time = gtk_settings.props.gtk_double_click_time
        if (self._last_click_x is not None
                and event.time < (self._last_click_time + double_click_time)
                and abs(event.x - self._last_click_x) <= double_click_distance
                and abs(event.y - self._last_click_y) <= double_click_distance
                ):
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
        if self.view == 'day':
            return self.selected_date
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

        max_width = 7 * self._day_width
        if x < 0:
            day_no = 0
        elif x > max_width:
            day_no = 6
        else:
            offset_x = (
                self._timeline.get_width(self) if self.view == 'week' else 0)
            day_no = int((x - offset_x) / self._day_width)
        return cur_week[day_no]

    def _handle_event_item_press(self, event_item, event):
        if event_item.event.editable:
            self._drag_x = event.x
            self._drag_y = event.y
            self._drag_height = 0
            self._drag_start_date = self.get_cur_pointed_date(event.x, event.y)
            self._drag_date = self._drag_start_date
            self.set_has_tooltip(False)
            event_item.transparent = True

            event_item.width = self._day_width - 6
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
                    # Remove other event items for this event
                    for item in event_item.event.event_items:
                        if item != event_item:
                            self._event_items.remove(item)

                    event_item.height = 2 * self._line_height
                    day_no = (int((event.x - self._timeline.get_width(self))
                        / self._day_width))
                    day_off = day_no * self._day_width + 2
                    event_item.x = self._timeline.get_width(self) + day_off
                    if (event_item.no_caption or event.y < event_item.y
                            or event.y > (event_item.y + event_item.height)):
                        level_height = self.minute_height * self.MIN_PER_LEVEL
                        cur_level = int((event.y - self._timeline.y)
                            / level_height)
                        nb_levels_per_hour = 60 / self.MIN_PER_LEVEL
                        cur_level -= nb_levels_per_hour
                        if cur_level < 0:
                            cur_level = 0
                        event_item.y = (
                            self._timeline.y + cur_level * level_height)
                        nb_minutes = cur_level * self.MIN_PER_LEVEL
                        hours, minutes = map(int, divmod(nb_minutes, 60))
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
                        self._event_items.remove(item)
                    else:
                        event_item.event.start += daysdelta
                        if event_item.event.end:
                            event_item.event.end += daysdelta
                        weekno = int(event.y / self._day_height)
                        day_no = int(event.x / self._day_width)
                        event_item.y = weekno * self._day_height
                        event_item.y += (
                            int(self._line_height) + 1)
                        event_item.x = (
                            day_no * self._day_width + 2)
                        item_height = (
                            self._line_height + 2)
                        while event_item.y < event.y:
                            event_item.y += item_height
                        event_item.y -= item_height
                        event_item.no_caption = False
            self.queue_draw()

        self.emit('event-pressed', event_item.event)

        if self._is_double_click(event):
            self._stop_drag_and_drop()
            self.emit('event-activated', event_item.event)

    def _stop_drag_and_drop(self):
        self._drag_x = None
        self._drag_y = None
        self._drag_height = 0
        self._drag_start_date = None
        self._drag_date = None
        self.set_has_tooltip(True)

    def _handle_event_item_motion(self, event_item, event):
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
            self.queue_draw()
            return

        # Handle horizontal translation
        if cur_pointed_date != self._drag_date:
            self._drag_date = cur_pointed_date
            event_item.event.start += daysdelta
            if event_item.event.end:
                event_item.event.end += daysdelta
            event_item.x += daysdelta.days * self._day_width

        if event_item.event.multidays or event_item.event.all_day:
            self.queue_draw()
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
            self.queue_draw()
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
        self.queue_draw()
        self._drag_height -= pxdelta

    def get_root_item(self):
        # Compatibility method for GooCanvas API
        return self

    def grab_focus(self, item=None):
        # Compatibility method for GooCanvas API
        super().grab_focus()


GObject.signal_new('event-pressed',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('event-activated',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('event-released',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('day-pressed',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('day-activated',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('day-selected',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('view-changed',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))
GObject.signal_new('page-changed',
    Calendar,
    GObject.SignalFlags.RUN_FIRST,
    GObject.TYPE_NONE,
    (GObject.TYPE_PYOBJECT,))


def parse_color(color_string):
    """Parse a color string to RGB values (0-1 range)."""
    color = Gdk.RGBA()
    if color.parse(color_string):
        return color.red, color.green, color.blue, color.alpha
    return 0, 0, 0, 1


class DayItem:
    """
    A data structure representing a day.
    """

    def __init__(self, cal, **kwargs):
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
        self.visible = True

    def contains_point(self, px, py):
        """Check if a point is within this day item."""
        return (self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height)

    def compute_line_height(self, cal):
        """Compute the line height based on font."""
        if not self.date:
            return

        week_day = self.date.weekday()
        day_name = calendar.day_name[week_day]
        caption = '%s %s' % (self.date.day, day_name)

        # Create a Pango layout to measure text
        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))
        layout.set_text(caption, -1)
        _, logical_rect = layout.get_pixel_extents()
        self.line_height = logical_rect.height

        # Compute number of lines that fit
        if self.full_border:
            box_height = max(self.height - self.line_height - 3, 0)
        else:
            box_height = max(self.height - self.line_height, 0)
        line_height_and_margin = self.line_height + 2
        self.n_lines = (
            int(box_height / line_height_and_margin)
            if line_height_and_margin > 0
            else 0)

    def draw(self, cr, cal):
        """Draw this day item using Cairo."""
        if not self.date:
            return

        week_day = self.date.weekday()
        day_name = calendar.day_name[week_day]
        caption = '%s %s' % (self.date.day, day_name)

        # Create a Pango layout
        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))
        layout.set_text(caption, -1)
        _, logical_rect = layout.get_pixel_extents()
        line_height = logical_rect.height
        self.line_height = line_height

        # Draw the border (filled rectangle)
        r, g, b, a = parse_color(self.border_color)
        cr.set_source_rgba(r, g, b, a)
        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.fill()

        # Draw the title text
        r, g, b, a = parse_color(self.title_text_color)
        cr.set_source_rgba(r, g, b, a)
        padding_left = 2
        cr.move_to(self.x + padding_left, self.y)
        PangoCairo.show_layout(cr, layout)

        # Draw the "body" of the day
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

        r, g, b, a = parse_color(self.body_color)
        cr.set_source_rgba(r, g, b, a)
        cr.rectangle(box_x, box_y, box_width, box_height)
        cr.fill()

        line_height_and_margin = line_height + 2
        self.n_lines = (
            int(box_height / line_height_and_margin)
            if line_height_and_margin > 0
            else 0)

        # Draw indicator if needed
        if self.show_indic:
            r, g, b, a = parse_color(self.title_text_color)
            cr.set_source_rgba(r, g, b, a)
            # Draw a triangle indicator
            x1 = self.x + self.width - line_height / 1.5
            y1 = self.y + line_height / 3
            x2 = x1 + line_height / 6
            y2 = y1 + line_height / 3
            x3 = x1 + line_height / 3
            y3 = y1
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.line_to(x3, y3)
            cr.close_path()
            cr.fill()


class EventItem:
    """
    A data structure representing an event.
    """

    def __init__(self, cal, **kwargs):
        self._cal = cal
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.left_border = 0
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color', 'black')
        self.event = kwargs.get('event')
        self.type = kwargs.get('type', 'leftright')
        self.time_format = kwargs.get('time_format')
        self.transparent = False
        self.no_caption = False
        self._line_height = None

    def get_line_height(self, cal):
        """Get the line height for this event item."""
        if self._line_height is not None:
            return self._line_height

        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))
        layout.set_text("Test", -1)
        _, logical_rect = layout.get_pixel_extents()
        self._line_height = logical_rect.height
        return self._line_height

    def contains_point(self, px, py):
        """Check if a point is within this event item."""
        return (self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height)

    def get_tooltip(self):
        """Get the tooltip text for this event."""
        startdate = self.event.start.strftime('%x')
        starttime = self.event.start.strftime(self.time_format)
        if self.event.end:
            enddate = self.event.end.strftime('%x')
            endtime = self.event.end.strftime(self.time_format)

        if self.event.all_day:
            if not self.event.end:
                return '%s\n%s' % (startdate, self.event.caption)
            else:
                return '%s - %s\n%s' % (startdate, enddate, self.event.caption)
        elif self.event.multidays:
            if not self.event.end:
                return '%s %s\n%s' % (startdate, starttime, self.event.caption)
            else:
                return '%s %s - %s %s\n%s' % (startdate, starttime,
                    enddate, endtime, self.event.caption)
        else:
            if not self.event.end:
                return '%s\n%s' % (starttime, self.event.caption)
            else:
                return '%s - %s\n%s' % (starttime, endtime, self.event.caption)

    def draw(self, cr, cal):
        """Draw this event item using Cairo."""
        if (self.event.all_day or cal.view == "month"
                or self.event.multidays):
            self._draw_all_day_event(cr, cal)
        else:
            self._draw_event(cr, cal)

    def _draw_event(self, cr, cal):
        self.width = max(self.width, 0)
        starttime = self.event.start.strftime(self.time_format)
        endtime = self.event.end.strftime(self.time_format)

        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))

        first_line = starttime + ' - ' + endtime
        layout.set_text(first_line, -1)
        _, logical_rect = layout.get_pixel_extents()
        line_height = logical_rect.height
        self._line_height = line_height

        if self.width < logical_rect.width:
            first_line = starttime + ' - '

        second_line = self.event.caption
        layout.set_text(second_line, -1)
        _, logical_rect = layout.get_pixel_extents()
        if self.width < logical_rect.width:
            second_line = None

        if self.height >= (2 * line_height):
            caption = first_line
            if second_line:
                caption += '\n' + second_line
        elif self.height >= line_height:
            caption = first_line
        else:
            caption = ''
        caption = '' if self.no_caption else caption
        the_event_bg_color = self.event.bg_color
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        if the_event_bg_color is not None:
            r, g, b, a = parse_color(the_event_bg_color)
            if self.transparent:
                a = 0.5
            cr.set_source_rgba(r, g, b, a)
            cr.rectangle(self.x, self.y, self.width, self.height)
            cr.fill()

        # Draw the text
        r, g, b, a = parse_color(the_event_text_color)
        cr.set_source_rgba(r, g, b, a)

        # Clip to event bounds
        cr.save()
        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.clip()

        layout.set_text(caption, -1)
        cr.move_to(self.x + 2, self.y)
        PangoCairo.show_layout(cr, layout)

        cr.restore()

    def _draw_all_day_event(self, cr, cal):
        self.width = max(self.width, 0)
        starttime = self.event.start.strftime(self.time_format)

        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))

        caption = self.event.caption
        if not self.event.all_day and not self.event.multidays:
            caption = '%s %s' % (starttime, caption)
        elif self.event.multidays:
            caption = '%s %s' % (starttime, caption)

        caption = '' if self.no_caption else caption
        layout.set_text(caption, -1)
        _, logical_rect = layout.get_pixel_extents()
        self.height = logical_rect.height
        self._line_height = logical_rect.height

        the_event_bg_color = self.event.bg_color
        if self.event.text_color is None:
            the_event_text_color = self.text_color
        else:
            the_event_text_color = self.event.text_color

        if the_event_bg_color is not None:
            r, g, b, a = parse_color(the_event_bg_color)
            if self.transparent:
                a = 0.5
            cr.set_source_rgba(r, g, b, a)
            cr.rectangle(self.x, self.y, self.width, self.height)
            cr.fill()

        # Draw the text
        r, g, b, a = parse_color(the_event_text_color)
        cr.set_source_rgba(r, g, b, a)

        # Clip to event bounds
        cr.save()
        cr.rectangle(self.x, self.y, self.width, self.height)
        cr.clip()

        cr.move_to(self.x + 2, self.y)
        PangoCairo.show_layout(cr, layout)

        cr.restore()


class TimelineItem:
    """
    A data structure representing a timeline.
    """

    def __init__(self, cal, **kwargs):
        self._cal = cal
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.height = kwargs.get('height', 0)
        self.line_color = kwargs.get('line_color')
        self.bg_color = kwargs.get('bg_color')
        self.text_color = kwargs.get('text_color')
        self.time_format = kwargs.get('time_format')
        self._width = None
        self._min_line_height = None
        self.visible = False

    def get_width(self, cal):
        """Compute the width needed for the timeline."""
        if self._width is not None:
            return self._width

        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))

        max_width = 0
        for n in range(24):
            caption = datetime.time(n).strftime(self.time_format)
            layout.set_text(caption, -1)
            ink_rect, logical_rect = layout.get_pixel_extents()
            max_width = max(max_width, logical_rect.width)

        self._width = max_width + 4  # Add some padding
        return self._width

    def get_min_line_height(self, cal):
        """Get the minimum line height for the timeline."""
        if self._min_line_height is not None:
            return self._min_line_height

        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))

        max_height = 0
        for n in range(24):
            caption = datetime.time(n).strftime(self.time_format)
            layout.set_text(caption, -1)
            _, logical_rect = layout.get_pixel_extents()
            max_height = max(max_height, logical_rect.height)

        self._min_line_height = max_height
        return self._min_line_height

    def get_line_height(self, cal):
        """Get the actual line height for drawing."""
        min_height = self.get_min_line_height(cal)
        if self.height > 0 and min_height < self.height // 24:
            return self.height // 24
        return min_height

    def draw(self, cr, cal):
        """Draw the timeline using Cairo."""
        width = self.get_width(cal)
        line_height = self.get_line_height(cal)
        min_line_height = self.get_min_line_height(cal)

        # Compute padding for centering text
        padding_top = 0
        if line_height > min_line_height:
            padding_top = (line_height - min_line_height) / 2

        pango_context = cal.get_pango_context()
        layout = Pango.Layout(pango_context)
        layout.set_font_description(
            Pango.FontDescription.from_string(cal.props.font))

        for n in range(24):
            y = self.y + n * line_height
            caption = datetime.time(n).strftime(self.time_format)

            # Draw background
            r, g, b, a = parse_color(self.bg_color)
            cr.set_source_rgba(r, g, b, a)
            cr.rectangle(self.x, y, width, line_height)
            cr.fill()

            # Draw line separator
            r, g, b, a = parse_color(self.line_color)
            cr.set_source_rgba(r, g, b, a)
            cr.rectangle(self.x, y, width, 1)
            cr.fill()

            # Draw text
            r, g, b, a = parse_color(self.text_color)
            cr.set_source_rgba(r, g, b, a)
            layout.set_text(caption, -1)
            cr.move_to(self.x, y + padding_top)
            PangoCairo.show_layout(cr, layout)
