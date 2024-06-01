def foo() -> None:
    """
    Calls a function that will raise and exception.

    ...
    """
    bar()


def bar() -> None:
    raise Exception("Custom exception")
