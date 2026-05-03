#!/bin/bash
set -euo pipefail

FETCH_SCRIPT="./collect_data.sh"
PARSE_INPUT_SCRIPT="./parse_input.sh"
SPLIT_SCRIPT="./split_work.sh"
CRAWLING_SCRIPT="./crawling.sh"

echo "Running WHOIS script..."
if ! "$FETCH_SCRIPT"; then
    echo "Error: fetch script failed" >&2
    exit 1
fi

echo "Data collection completed successfully"

echo "Parsing INPUT script..."
if ! "$PARSE_INPUT_SCRIPT"; then
    echo "Error: parsing whois failed" >&2
    exit 1
fi

echo "Data parsing completed successfully"

echo "Parsing INPUT script..."
if ! "$SPLIT_SCRIPT"; then
    echo "Error: splitting failed" >&2
    exit 1
fi

echo "Splitting completed successfully"

echo "Crawling job submitting..."
if ! "$CRAWLING_SCRIPT"; then
    echo "Error: splitting failed" >&2
    exit 1
fi

echo "Crawling job submitted"
