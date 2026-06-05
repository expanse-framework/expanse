import logging


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        from expanse.logging.utils import context

        context_ = context()
        if not hasattr(record, "context") and context_ is not None:
            record.context = context_._data

        return True
