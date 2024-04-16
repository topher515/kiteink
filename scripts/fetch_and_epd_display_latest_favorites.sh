#!/usr/bin/env bash
fetch_spots_json.py --threaded 1374 416 411 | paint_report_from_json.py --epaper
