import re


FILENAME_PATTERN = (
    r"^(\d{2}\.\d{2}\.\d{2})-(\d{2}:\d{2}:\d{2})_(\d{3}_\d{9}|\d{9}_\d{3})\.mp3$"
)


def validate_filename(filename: str) -> bool:
    return bool(re.match(FILENAME_PATTERN, filename))
