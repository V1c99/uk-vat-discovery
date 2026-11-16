# UK company VAT numbers from the open web

My take-home for the Veridion Data Assets Intern track ("VAT Identifier Discovery"). The question is
whether a dataset of UK company VAT numbers can be built from the open web, proven on a sample.

Work in progress. What I ran and what came back is in `research/log.md`, and every number is
printed by `sql/numbers.sql`.

## How to run

The Companies House snapshot goes in `data/ch/` first, see `data/README.md`.

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,probes]
python -m ukvat.run_sql sql/profile.sql sql/sample.sql
python -m ukvat.websites sample/register.csv results/websites
python -m ukvat.run_sql sql/numbers.sql
pytest
```

The probes are in `experiments/`, each one has its command at the top and in the log.
