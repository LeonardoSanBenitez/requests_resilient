import requests
from requests import *
import sys
import time

__version__ = "0.0.1"

def get(**kwargs): #TODO: to support poitional parameters
    max_retries = 10
    wait = 1 #seconds
    
    retries = 1
    response = None
    while True:
        try:
            response = requests.get(**kwargs)
            break
        except Exception as e:
            sys.stdout.flush()
            time.sleep(wait)
            retries += 1
            if retries > max_retries:
                break
    return response

def post(**kwargs):
    max_retries = 30
    wait = 1 #seconds
    
    retries = 1
    response = None
    while True:
        try:
            response = requests.post(**kwargs)
            break
        except Exception as e:
            sys.stdout.flush()
            time.sleep(wait)
            retries += 1
            if retries > max_retries:
                break
    return response


#r = get('https://google.com')
#assert r.status_code == 200