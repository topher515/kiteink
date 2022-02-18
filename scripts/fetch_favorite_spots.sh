#!/usr/bin/env bash

# Fetch lanikai, kaneohe, 
fetch_spots_json.py --threaded 187573 640 89493 > data/latest_favorite_spots.json
# python3 fetch_spots_json.py 429 187573 430 > data/latest_favorite_spots.json