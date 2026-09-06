#!/bin/bash
set -e
cd /Users/twinssn/Projects2/imhero
.venv/bin/python pipeline.py 5 --publish >> launchd_stdout.log 2>> launchd_stderr.log
