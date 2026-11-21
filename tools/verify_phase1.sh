#!/bin/sh
# Chạy bộ kiểm thử trước khi gắn tag.
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="tests:.${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
