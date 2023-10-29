import sys
import time
from typing import Optional, Callable
import asyncio
import aiohttp
import logging

from requests_resilient.errors import MaxRetriesExceededError


# verify_function is a function that takes a response and returns True if the response is good
def verify_function_default(response):
    if response is None:
        return False
    elif response.status_code//100 == 5:
        return False
    else:
        return True


async def _async_request(*args, method: str, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    '''
    @param wait Is given in seconds
    '''
    retries = 1
    response = None
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with getattr(session, method)(*args, **kwargs) as response:
                    # Convert to `requests`-style response
                    response.status_code = response.status
                    response.text = await response.text()  # str
                    try:
                        r = await response.json(content_type=None)
                        response.json = lambda: r  # Callable
                    except Exception as e:
                        pass

                    # Verify
                    if verify_function(response) is False:
                        text = f'Verify function failed with status code {response.status_code} and message {response.text[:5000]}'
                        logging.info(text)
                        raise RuntimeError(text)
                    break
        except Exception as e:
            sys.stdout.flush()
            await asyncio.sleep(wait)
            retries += 1
            if retries > max_retries:
                raise MaxRetriesExceededError(f'Max retries exceeded. Last error was {e}')
            logging.info('Retrying...')
    return response


async def async_get(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='get', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


async def async_post(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='post', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


async def async_put(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='put', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


async def async_patch(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='patch', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


async def async_delete(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='delete', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


async def async_head(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='head', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


async def async_options(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return await _async_request(*args, method='options', verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)
