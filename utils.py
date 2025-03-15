import datetime
import pytz
import os

def get_last_updated_time(timestr):
    # Convert to datetime object with microseconds
    utc_dt = datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%f")

    # Define the local timezone (e.g., 'America/New_York', 'Asia/Tokyo', etc.)
    local_tz = pytz.timezone(os.getenv("LOCAL_TIMEZONE", "UTC"))

    # Convert UTC datetime to local timezone
    utc_dt = pytz.utc.localize(utc_dt)
    local_dt = utc_dt.astimezone(local_tz)

    # Format it in a readable form
    last_updated = local_dt.strftime("%d %b %Y %I:%M:%S %p")

    return last_updated
