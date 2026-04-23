from datetime import datetime, timedelta, timezone

def build_time_window(start_time, duration_seconds):
    """
    Input:
        start_time: "2026-03-21 08:29:06" hoặc ISO string
        duration_seconds: int

    Output:
        since, until (UTC, format xAPI)
    """

    # parse linh hoạt
    try:
        dt = datetime.fromisoformat(start_time)
    except:
        dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")

    # nếu không có timezone → assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # convert về UTC
    dt_utc = dt.astimezone(timezone.utc)

    since = dt_utc
    until = dt_utc + timedelta(seconds=duration_seconds)

    fmt = "%Y-%m-%dT%H:%M:%SZ"

    return since.strftime(fmt), until.strftime(fmt)