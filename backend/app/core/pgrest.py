"""PostgREST query-string helpers."""

from urllib.parse import quote


def q(value) -> str:
    """Percent-encode a value for use inside a PostgREST filter.

    URLs, keywords like "barnes & noble", and timestamps with "+00:00"
    all contain characters (&, +, #, ,) that corrupt the query string or
    get decoded to the wrong value server-side if left raw.
    """
    return quote(str(value), safe="")


def ts(dt) -> str:
    """Format a datetime for a PostgREST filter against a naive TIMESTAMP column.

    Strips the UTC offset so no '+' appears in the query string ('+' decodes
    to a space and makes Postgres reject the timestamp entirely).
    """
    return dt.replace(tzinfo=None).isoformat()
