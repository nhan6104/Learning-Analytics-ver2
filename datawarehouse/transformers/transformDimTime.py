from datetime import datetime


class transformDimTime:
    def __init__(self):
        pass

    def transform(self, statement, kwargs = {}):
        timeStamp = statement.timestamp if statement.timestamp else ""
        ts = datetime.fromisoformat(timeStamp)

        week = ts.isocalendar().week
        day_of_week = ts.isocalendar().weekday  # Monday=1
        date = ts.day
        month = ts.month
        year = ts.year

        hour = ts.hour
        if 5 <= hour <= 11:
            time_slot = "Morning"
        elif 12 <= hour <= 16:
            time_slot = "Afternoon"
        elif 17 <= hour <= 20:
            time_slot = "Evening"
        else:
            time_slot = "Night"

        self.timeId = f"{time_slot[0]}{year}{month}{date}{week}{day_of_week}"

        return {
            "time_id": self.timeId,
            "date": date,
            "week": week,
            "month": month,
            "year": year,
            "day_of_week": day_of_week,
            "time_slot": time_slot,
        }