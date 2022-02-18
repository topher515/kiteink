
#!/usr/bin/env bash

ssh -t pi@$RPI_IP "cd /home/pi/app && PIPENV_VENV_IN_PROJECT=1 WF_USERNAME='$WF_USERNAME' WF_PASSWORD='$WF_PASSWORD' pipenv run scripts/fetch_and_epd_display_latest_favorites.sh"