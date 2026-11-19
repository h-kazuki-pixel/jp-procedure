#!/bin/sh
# 元のデータ(デジタル庁の Excel)を data/raw/ に取り、SHA-256 を確かめる。作り直しの最初に 1 回だけ動かす。
set -eu
mkdir -p data/raw
B=https://www.digital.go.jp/assets/contents/node/basic_page/field_ref_resources/b931f8c1-8598-45ee-91b1-1e9a45acd301
curl -fL -o data/raw/20260826_procedures_survey_result_outline_02.xlsx "$B/851f67ec/20260826_procedures_survey_result_outline_02.xlsx"
sleep 1
curl -fL -o data/raw/20250729_procedures-survey-results_outline_02.xlsx "$B/f8b0669f/20250729_procedures-survey-results_outline_02.xlsx"
date -u +%Y-%m-%dT%H:%M:%SZ > data/raw/downloaded_at.txt
cd data/raw && grep xlsx ../../scripts/SHA256SUMS | shasum -a 256 -c -
