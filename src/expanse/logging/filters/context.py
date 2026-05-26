import logging


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        from expanse.logging.utils import context

        if not hasattr(record, "context") and context() is not None:
            record.context = context()._data

        return True
