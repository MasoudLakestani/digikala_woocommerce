# Project README

This project contains commands for working with a Scrapy-based crawler and managing a Python virtual environment.

## Activate Virtual Environment

To activate the virtual environment, use:

```bash
source .venv/bin/activate
```
## Crawl Product URLs

To find product URLs listed in the category_url.txt file, run:
```bash
scrapy crawl url
```

## Crawl Products

To crawl the products found in the previous step, run:

```bash

scrapy crawl product
```