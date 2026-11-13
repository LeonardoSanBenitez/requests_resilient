# Contributing

## Setting up

Clone the repository, create a virtual environment, then install the development dependencies:

```bash
git clone https://github.com/LeonardoSanBenitez/requests_resilient.git
cd requests_resilient
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows the activate script is `.venv\Scripts\activate`.

Python 3.10 or newer is required.

## Running the checks

One command runs every check CI runs (mypy in strict mode, ruff lint, ruff format, the tests):

```bash
bash scripts/run_tests.sh
```

Or run them one at a time:

```bash
mypy ./src
ruff check ./src ./tests
ruff format --check ./src ./tests
python3 -m unittest discover -s tests
```

To test in a container:

```bash
docker build -f Dockerfile.test -t requests-resilient-test .
docker run --rm requests-resilient-test
```

## Making a change

Open an issue first for anything beyond a small fix, so the approach can be agreed before work is spent. Put one logical change per pull request. New behaviour must come with tests, and the code must pass mypy in strict mode. Add a line under an `## Unreleased` heading at the top of `CHANGELOG.md` (create that heading if it is missing) describing the change from the user's point of view.

## Public API changes

The public API is what `requests_resilient/__init__.py` exports. A change to it needs a short written proposal in the issue first: what problem, what the new interface is, and what breaks. The versioning rule stated at the top of `CHANGELOG.md` applies: patch releases fix behaviour, minor releases add to the public API without changing what already exists, and major releases may change it with a documented migration.

## Reporting a security problem

Do not open a public issue. See `SECURITY.md`.
