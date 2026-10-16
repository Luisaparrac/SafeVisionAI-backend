"""Date filters of the panel: local days, both ends inclusive."""

from datetime import date, datetime, time, timedelta, tzinfo

from safevision.domain.errors import ValidationError


def local_day_range(
    date_from: date | None, date_to: date | None, timezone: tzinfo
) -> tuple[datetime | None, datetime | None]:
    """Instants ``[start of date_from, start of the day after date_to)`` in ``timezone``.

    Dates are read in the zone where the panel shows ``date`` and ``time``.
    ``None`` leaves that end open; a reversed range is a ValidationError.
    """
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValidationError("La fecha 'desde' no puede ser posterior a 'hasta'")

    def start_of(day: date | None) -> datetime | None:
        return None if day is None else datetime.combine(day, time.min, tzinfo=timezone)

    return start_of(date_from), start_of(date_to + timedelta(days=1) if date_to else None)
