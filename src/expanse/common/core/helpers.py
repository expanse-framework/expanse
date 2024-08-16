from __future__ import annotations


class PlaceholderPath:
    def __init__(self, app_path: str, relative_path: str) -> None:
        self.app_path = app_path
        self.relative_path = relative_path


def path(relative_path: str | None = None) -> PlaceholderPath:
    """
    Returns a placeholder Path that will be resolved relative to the application
    when it is bootstrapped.
    """
    return PlaceholderPath("base", relative_path or "")


def static_path(relative_path: str | None = None) -> PlaceholderPath:
    """
    Returns a placeholder Path that will be resolved relative to the application
    when it is bootstrapped.
    """
    return PlaceholderPath("static", relative_path or "")


def resource_path(relative_path: str) -> PlaceholderPath:
    """
    Returns a placeholder Path that will be resolved relative to the application
    when it is bootstrapped.
    """
    return PlaceholderPath("resources", relative_path)
