from typing import Optional
import shutil
from requests_resilient.synchronous import get


def download_file(url, local_filename: Optional[str] = None):
    if not local_filename:
        local_filename = url.split('/')[-1]
    assert type(local_filename) is str, f'local_filename must be a string, but is {type(local_filename)}'
    with get(url=url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename
