import datetime
from obspy.core.utcdatetime import UTCDateTime

MARS_TO_MONTH_INT_CONVERSION = {
    'JAN': '1',
    'FEB': '2',
    'MARCH': '3',
    'APRIL': '4',
    'MAY': '5',
    'JUN': '6',
    'JUL': '7',
    'AUG': '8',
    'SEPT': '9',
    'OCT': '10',
    'NOV': '11',
    'DEC': '12',
}

STAND_TO_MARS_MONTH_CONVERSION = {
    'Jan': 'JAN',
    'Feb': 'FEB',
    'Mar': 'MARCH',
    'Apr': 'APRIL',
    'May': 'MAY',
    'Jun': 'JUN',
    'Jul': 'JUL',
    'Aug': 'AUG',
    'Sep': 'SEPT',
    'Oct': 'OCT',
    'Nov': 'NOV',
    'Dec': 'DEC'
}

MARS_TO_STAND_MONTH_CONVERSION = {}
for key, value in STAND_TO_MARS_MONTH_CONVERSION.items():
    MARS_TO_STAND_MONTH_CONVERSION[value] = key


def date_conv_mars_to_stand(filename):
    date_only = filename.split('.')[0][:-3]
    year, month, day = date_only.split('-')
    month = MARS_TO_STAND_MONTH_CONVERSION[month]
    return year + '-' + month + '-' + day


def date_conv_stand_to_mars(date, suffix='.UVW_calib_ACC.mseed'):
    date = yyyy_mm_dd_to_datetime(date)
    year, month, day = date.split('-')
    month = STAND_TO_MARS_MONTH_CONVERSION[month]
    return year + '-' + month + '-' + day + suffix


def yyyy_mm_dd_to_datetime(yyyy_mm_dd):
    return datetime.datetime.strptime(yyyy_mm_dd,
                                      '%Y-%m-%d').strftime("%Y-%b-%d")


def get_time_interval(window_key, window_size=2**17, frequency=20.0):
    batch = window_key.split('_')[-1]
    year, month, day = window_key.split('-')

    day = day.split('.')[0]
    month = MARS_TO_MONTH_INT_CONVERSION[month]

    batch = int(batch)

    dt = 1 / frequency
    start_time = (batch /2) * dt * window_size
    end_time = ((batch/2) + 1) * dt * (window_size - 1)

    str_start_time = UTCDateTime(year + '-' + str(month) + '-' + day)
    str_start_time = str_start_time.__add__(start_time)

    str_end_time = UTCDateTime(year + '-' + str(month) + '-' + day)
    str_end_time = str_end_time.__add__(end_time)

    return str_start_time, str_end_time
