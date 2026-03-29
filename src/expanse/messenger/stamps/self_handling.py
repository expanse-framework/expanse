from dataclasses import dataclass


@dataclass
class SelfHandlingStamp:
    """
    A stamp to indicate that a message is its own handler.

    This assume that the message class has a `handle` method
    that can be called to handle the message.

    This stamp is used internally for jobs/tasks dispatched by the queue module.
    """
