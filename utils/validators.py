import re

DATE_REGEX = re.compile(r'^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\d{4}$')

def is_valid_ddmmyyyy(date_str):
    if not date_str:
        return True  # allow empty
    return bool(DATE_REGEX.match(date_str))
