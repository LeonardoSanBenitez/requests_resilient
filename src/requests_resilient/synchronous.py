import requests
import sys
import time
from typing import Optional, Callable
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


def _request(*args, method: Callable, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    '''
    @param wait Is given in seconds
    '''
    retries = 1
    response = None
    while True:
        try:
            response = method(*args, **kwargs)
            # from requests_toolbelt.utils import dump
            # logging.debug(dump.dump_all(response).decode(errors="ignore")[:5000])
            if verify_function(response) is False:
                text = f'Verify function failed with status code {response.status_code} and message {response.text[:5000]}'
                logging.info(text)
                raise RuntimeError(text)
            break
        except Exception as e:
            sys.stdout.flush()
            time.sleep(wait)
            retries += 1
            if retries > max_retries:
                raise MaxRetriesExceededError(f'Max retries exceeded. Last error was {e}')
            logging.info('Retrying...')
    return response


def get(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.get, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


def post(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.post, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


def put(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.put, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


def patch(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.patch, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


def delete(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.delete, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


def head(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.head, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)


def options(*args, verify_function: Callable = verify_function_default, max_retries: int = 10, wait: int = 1, **kwargs):  # type: ignore
    return _request(*args, method=requests.options, verify_function=verify_function, max_retries=max_retries, wait=wait, **kwargs)
