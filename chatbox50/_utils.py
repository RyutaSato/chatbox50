import asyncio
import logging
import inspect

logger = logging.getLogger(__name__)


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
        caller = inspect.currentframe().f_back
        logger.error(f"Called from {caller.f_code.co_filename}, line {caller.f_lineno}, function "
                     f"{caller.f_code.co_name} doesn't set. the process was skipped")
        if raise_error:
            raise AttributeError(f"詳細はlogを参照")
        return
    if not callable(func):
        if raise_error:
            raise AttributeError(f"func must be callable")
        return
    if asyncio.iscoroutinefunction(func):
        await func(*args, **kwargs)
    else:
        await asyncio.to_thread(func, *args, **kwargs)
