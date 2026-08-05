import re


_DURATION_STRING_REGEX = re.compile(r'^(-?(?:\d+)?\.?\d+) *(m(?:illiseconds?|s(?:ecs?)?))?(s(?:ec(?:onds?|s)?)?)?(m(?:in(?:utes?|s)?)?)?(h(?:ours?|rs?)?)?(d(?:ays?)?)?(w(?:eeks?|ks?)?)?$')
_SIZE_STRING_REGEX = re.compile(r'^(-?(?:\d+)?\.?\d+) *(b|kb|mb|gb|tb|pb)$')


def duration(duration_: int | str) -> int:
    """
    Parse a duration string into an integer representing the duration in milliseconds.

    :param duration_: duration in milliseconds

    :return: integer representing the duration in milliseconds
    """
    if isinstance(duration_, int):
        return duration_

    m = _DURATION_STRING_REGEX.match(duration_.lower())

    if not m:
        raise ValueError(f'Invalid duration {duration_}')

    value = int(m.group(1))

    if m.group(3):
        return value * 1000

    if m.group(4):
        return value * 1000 * 60

    if m.group(5):
        return value * 1000 * 60  * 60

    if m.group(6):
        return value * 1000 * 60 * 60 * 24

    if m.group(7):
        return value * 1000 * 60 * 60 * 24 * 7

    return value


def size(size_: int | str) -> int:
    """
    Parse a size string into an integer representing the size in bytes.

    :param size_: size in bytes

    :return: integer representing the size in bytes
    """
    if isinstance(size_, int):
        return size_

    m = _SIZE_STRING_REGEX.match(size_.lower())

    if not m:
        raise ValueError(f'Invalid size {size_}')

    value = int(m.group(1))
    match m.group(2):
        case 'b':
            return value

        case 'kb':
            return value * 1024

        case 'mb':
            return value * 1024 * 1024

        case 'gb':
            return value * 1024 ** 3

        case 'tb':
            return value * 1024 ** 4

        case 'pb':
            return value * 1024 ** 5

        case _:
            raise ValueError(f'Invalid size {size_}')