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

Preferred first source is offline parser test pickles from LMQR. They contain saved parse results with an email object, parse status, and parsed dataframe for successful cases.

Potential source path:

```text
S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/test
```

Production parser references:

- `S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/test/compare_parser_to_pickles.py`
- `S:/QR/GitHub/LibreMax-QR/master/LMQR/NLP_Parsers/nlp_utils.py`
- `S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/clean_post_parse.py`
- `S:/QR/GitHub/LibreMax-QR/master/LMQR/colorparser/parse_handler.py`

`parse_handler.py` and `db_handler.py` are write paths and should not be invoked by this project.

## Commands

Inventory available offline parser pickles:

```powershell
python llm_clo_parser/run.py inventory-pickles --sector clo
```

Use an explicit pickle directory if needed:

```powershell
python llm_clo_parser/run.py inventory-pickles --sector clo --pickle-dir "S:/path/to/pickles"
```

Later commands will add dataset freezing, extraction, evaluation, and reporting.

## Model Setup

Install and run Ollama locally, then pull the default MVP model:

```powershell
ollama pull qwen3:8b
ollama run qwen3:8b
```

The extractor should use schema-constrained JSON output through Ollama's local API at `http://localhost:11434/api/chat`.
