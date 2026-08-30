class CustomError(Exception):
    pass


async def foo() -> None:
    """
    Calls a function that will raise and exception.

    ...
    """
    await bar()


async def bar() -> None:
    raise CustomError("Custom exception")
