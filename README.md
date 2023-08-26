# Requests Resilient

Wrapper around the `requests` python library to make it resilient to network failures

## Roadmap
* Implement other network patterns for resiliency:
  * Time-out
  * Deadlines
  * Circuit breaker
  * Fail-fast
* Expose both the `requests` compatible interface (`requests.get(...`) and an object oriented interface (`requester = Requester(); requester.get(...`)
* Make the library pip installable
