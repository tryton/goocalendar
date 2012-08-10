#This file is part of GooCalendar.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import sys
import datetime
import calendar


def my_weekdatescalendar(cal, *date):
    weeks = cal.monthdatescalendar(*date[:2])
    for weekno, week in enumerate(weeks):
        # Hide all days that are not part of the current week.
        weekdays = [d.timetuple()[:3] for d in week]
        if date[:3] in weekdays:
            return week
    raise Exception('No such week')


def my_monthdatescalendar(cal, *args):
    # Months that have only five weeks are filled with another week from
    # the following month.
    weeks = cal.monthdatescalendar(*args[:2])
    if len(weeks) < 6:
        last_day = weeks[-1][-1]
        offset = datetime.timedelta(1)
        week = []
        for i in range(7):
            last_day += offset
            week.append(last_day)
        weeks.append(week)
    return weeks


def first_day_of_week(cal, date):
    firstweekday = cal.firstweekday
    year, month, day = date[:3]
    day_shift = (calendar.weekday(year, month, day) + 7 - firstweekday) % 7
    return datetime.datetime(year, month, day) - datetime.timedelta(day_shift)


def previous_month(cal, date):
    year, month, day = date.timetuple()[:3]
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    prev_month_days = [d for d in cal.itermonthdays(year, month)]
    if day not in prev_month_days:
        day = max(prev_month_days)
    return datetime.datetime(year, month, day)


def next_month(cal, date):
    year, month, day = date.timetuple()[:3]
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
    next_month_days = [d for d in cal.itermonthdays(year, month)]
    if day not in next_month_days:
        day = max(next_month_days)
    return datetime.datetime(year, month, day)


def previous_week(cal, date):
    return date - datetime.timedelta(7)


def next_week(cal, date):
    return date + datetime.timedelta(7)


def time_delta(datetime1, datetime2):
    delta = datetime1 - datetime2
    if delta < datetime.timedelta():
        return -delta
    return delta


def event_days(event1, event2):
    end1 = event1.end if event1.end else event1.start
    end2 = event2.end if event2.end else event2.start
    return (time_delta(event1.start, end1).days
         - time_delta(event2.start, end2).days)


def event_intersects(event, start, end=None):
    end = end if end else start
    event_end = event.end if event.end else event.start
    return ((event.start >= start and event.start < end)
        or (event_end > start and event_end <= end)
        or (event.start < start and event_end > end))


def get_intersection_list(list, start, end):
    intersections = []
    for event in list:
        if event_intersects(event, start, end):
            intersections.append(event)
    return intersections


def count_intersections(list, start, end):
    intersections = 0
    for event in list:
        if event_intersects(event, start, end):
            intersections += 1
    return intersections


def count_parallel_events(list, start, end):
    """
    Given a list of events, this function returns the maximum number of
    parallel events in the given timeframe.
    """
    parallel = 0
    i = 0
    for i, event1 in enumerate(list):
        if not event_intersects(event1, start, end):
            continue
        parallel = max(parallel, 1)
        for f in range(i + 1, len(list)):
            event2 = list[f]
            new_start = max(event1.start, event2.start)
            new_end = min(event1.end, event2.end)
            if (event_intersects(event2, start, end)
                    and event_intersects(event2, new_start, new_end)):
                n = count_parallel_events(list[f:], new_start, new_end)
                parallel = max(parallel, n + 1)
    return parallel


def next_level(cur_time, min_per_level):
    """
    Given a datetime and the duration (in minutes) of time levels,
    return the datetime of the next level
    """
    delta_per_level = datetime.timedelta(minutes=min_per_level)
    delta_min = cur_time.minute % min_per_level
    delta_sec = cur_time.second
    cur_delta = datetime.timedelta(minutes=delta_min, seconds=delta_sec)
    next_level = cur_time - cur_delta + delta_per_level
    return next_level


def prev_level(cur_time, min_per_level):
    """
    Given a datetime and the duration (in minutes) of time levels,
    return the datetime of the previous level
    """
    delta_per_level = datetime.timedelta(minutes=min_per_level)
    delta_min = cur_time.minute % min_per_level
    cur_delta = datetime.timedelta(minutes=delta_min)
    prev_level = cur_time - cur_delta
    if prev_level == cur_time:
        prev_level -= delta_per_level
    return prev_level


def color_to_string(color):
    hexstring = "#%02X%02X%02X" % (
        color.red / 256, color.blue / 256, color.green / 256)
    return hexstring


def colors_to_rgba(red, green, blue, alpha):
    values = [alpha, blue, green, red]
    rgba_color = 0
    base = 1
    for value in values:
        rgba_color += value * base
        base *= 256
    return rgba_color


def rgba_to_colors(rgba):
    i = 0
    colors = []
    base = 256
    prev_base = 1
    while i < 4:
        value = (rgba % base) / prev_base
        colors.append(value)
        rgba -= value
        prev_base = base
        base *= 256
        i += 1
    return colors[3], colors[2], colors[1], colors[0]


if sys.version_info >= (2, 7):
    from functools import total_ordering
else:
    # This code comes from python standard library
    def total_ordering(cls):
        """Class decorator that fills in missing ordering methods"""
        convert = {
            '__lt__': [('__gt__', lambda self, other: not (self < other or self == other)),
                       ('__le__', lambda self, other: self < other or self == other),
                       ('__ge__', lambda self, other: not self < other)],
            '__le__': [('__ge__', lambda self, other: not self <= other or self == other),
                       ('__lt__', lambda self, other: self <= other and not self == other),
                       ('__gt__', lambda self, other: not self <= other)],
            '__gt__': [('__lt__', lambda self, other: not (self > other or self == other)),
                       ('__ge__', lambda self, other: self > other or self == other),
                       ('__le__', lambda self, other: not self > other)],
            '__ge__': [('__le__', lambda self, other: (not self >= other) or self == other),
                       ('__gt__', lambda self, other: self >= other and not self == other),
                       ('__lt__', lambda self, other: not self >= other)]
        }
        roots = set(dir(cls)) & set(convert)
        if not roots:
            raise ValueError('must define at least one ordering operation: < > <= >=')
        root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
        for opname, opfunc in convert[root]:
            if opname not in roots:
                opfunc.__name__ = opname
                opfunc.__doc__ = getattr(int, opname).__doc__
                setattr(cls, opname, opfunc)
        return cls
