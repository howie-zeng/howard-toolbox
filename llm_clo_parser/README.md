# LLM CLO Parser

Offline benchmark for parsing CLO dealer color and bond-offer text into validated structured-credit features.

This project lives in Howard Toolbox so it can be developed away from production parser code. LMQR parser files are read-only references only. Do not write to LMQR, production mailboxes, or production datasets from this tool.

## First Goal

Build a frozen internal evaluation set, then compare:

- regex baseline
- local Ollama LLM extractor, starting with `qwen3:8b`
- optional benchmarks with `qwen3:14b` and `llama3.1:8b`

## Local Folders

These folders are intentionally gitignored:

- `data/`: internal-only frozen eval files and manual review samples
- `outputs/`: predictions, metrics, and reports

## Data Sources

Default workflow uses a flat local CSV export so the project can run in the default Howard Toolbox Python environment, without LMQR runtime dependencies.

Expected local file:

```text
llm_clo_parser/data/frozen_eval.csv
```

Minimum columns:

- `sample_id`
- `text`

Recommended columns:

- `source_kind`
- `dealer`
- `listing_type`
- `price_type`
- `asset_type`
- `as_of_datetime`
- `listing_datetime`
- `is_excel`
- `ticker`
- `cusip`
- `tranche`
- `side`
- `bid_price`
- `offer_price`
- `bid_spread`
- `offer_spread`
- `bid_size`
- `offer_size`
- `rating`
- `wal`
- `yield`

LMQR remains the read-only source for understanding the original parser and for creating the CSV export outside this tool:

- `S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/test/compare_parser_to_pickles.py`
- `S:/QR/GitHub/LibreMax-QR/master/LMQR/NLP_Parsers/nlp_utils.py`
- `S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/clean_post_parse.py`
- `S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/parse_handler.py`

`parse_handler.py` and `db_handler.py` are write paths and should not be invoked by this project.

## Commands

Export the cached CLO training data to the local CSV bridge:

```powershell
python llm_clo_parser/run.py export-train-pkl `
  --input "S:/QR/Models/NLP_Parse/train_new/train_pkl.pkl" `
  --asset-class CLO `
  --output llm_clo_parser/data/frozen_eval.csv
```

By default this exports labeled rows only. Add `--include-negative` if you also want unlabeled context/header rows.

Inventory the local CSV export:

```powershell
python llm_clo_parser/run.py inventory-csv --input llm_clo_parser/data/frozen_eval.csv
```

Optional legacy diagnostic for offline parser pickles. This may require LMQR runtime dependencies such as `exchangelib`:

```powershell
python llm_clo_parser/run.py inventory-pickles --sector clo
```

Later commands will add extraction, evaluation, and reporting.

## Model Setup

Install and run Ollama locally, then pull the default MVP model:

```powershell
ollama pull qwen3:8b
ollama run qwen3:8b
```

The extractor should use schema-constrained JSON output through Ollama's local API at `http://localhost:11434/api/chat`.
