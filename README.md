# Requests Resilient

Wrapper around the `requests` python library to make it resilient to network failures

# Getting started
## Synchronous requests
Example:
```python
r = requests_resilient.get('https://google.com')
print(r.status_code)  # int, 200
print(r.text)  # str
```

## Assynchronous requests
Example:
```python
r = await requests_resilient.async_get('https://google.com')
print(r.status_code)  # int, 200
print(r.text)  # str
```