#!/usr/bin/env bash
python3 fetch_spots_json.py --threaded 187573 640 89493 | python3 paint_report_from_json.py --epaper