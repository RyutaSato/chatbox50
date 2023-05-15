import asyncio
import logging
from uuid import UUID
from typing import Type, TypeVar

ImmutableType = Type[int | str | UUID | complex | tuple | bytes]
Immutable = TypeVar("Immutable", int, str, UUID, complex, tuple, bytes)


async def run_as_await_func(func=None, *args, raise_error=False, **kwargs):
    """
    関数が非同期処理の場合はそのまま，同期処理の場合は，別のスレッドで実行されます．
    また，関数が入力されなかった場合は実行せずにNoneを返します．これはコールバックが登録されていない状況を考慮しています．
    Args:
        raise_error(bool): default False. If True, raise Error when func isn't set or not callable
        func(callable | None): callable object you want to run whichever it's blocking or non-blocking function
        *args:
        **kwargs:

    Returns:
        None
    """
    if func is None:
        if raise_error:
            raise AttributeError(f"Called from {__name__}, the func is None, raise_error: {raise_error}, {str(kwargs)}")
        await asyncio.sleep(0)
        return
    if not callable(func):
        if raise_error:
            raise AttributeError(f"func must be callable")
        await asyncio.sleep(0)
        return
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return await asyncio.to_thread(func, *args, **kwargs)


def str_converter(value: Immutable):
    if value is UUID:
        return str(value.hex)
    else:
        return str(value)


def get_logger_with_nullhandler(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    return logger
