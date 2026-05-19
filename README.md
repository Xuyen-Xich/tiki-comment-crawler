# Tiki Crawling Framework (Refactored)

This project is a production-ready, modular crawling framework for Tiki.vn.
It organizes code into reusable services, crawlers, and pipelines.

Features
- Playwright-based menu crawler (async)
- HTTP-based product and comment crawlers with retry and rate limiting
- Keyword search crawler
- Ranking service with weighted scoring
- Pydantic models for validation
- Export to CSV/XLSX/Parquet
- Logging with loguru

## Quick start
```powershell
python -m venv .venv
.venv\Scripts\activate
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

# Run an example
## Full pipeline (menu -> products -> comments)
```powershell
python main.py --mode full
```

## Keyword pipeline
```powershell
python main.py --mode keyword --keywords "Iphone"
```

# Project structure
```
project/
├── config/
├── core/
├── crawlers/
├── services/
├── pipelines/
├── models/
├── outputs/
├── notebooks/
├── tests/
├── main.py
├── requirements.txt
└── README.md
```

Notes
- Adjust configuration via environment variables or `config/settings.py`.
- This framework is designed for teaching and demoing production-ready crawling patterns.

License
MIT
