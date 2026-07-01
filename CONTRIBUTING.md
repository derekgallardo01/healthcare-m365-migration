# Contributing

## Development setup

```bash
git clone https://github.com/derekgallardo01/healthcare-m365-migration
cd healthcare-m365-migration
pip install -e ".[graph]"
```

## Running tests

```bash
python -m pytest -q
```

## Running the golden evals

```bash
python evals/run.py
```

Every eval in `evals/golden.json` runs against the bundled mock tenant.
Add new cases by editing that file and providing a path + assertion.

## Pull-request checklist

- [ ] All tests pass locally (`python -m pytest -q`)
- [ ] All evals pass locally (`python evals/run.py`)
- [ ] If you added a new HIPAA check, it has a CFR citation and remediation
- [ ] If you touched the backend surface, both the mock and the sketched
      Graph backend have matching method signatures
- [ ] CHANGELOG.md updated with a description of the change
