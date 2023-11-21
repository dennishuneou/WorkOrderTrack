#!/bin/bash
. /home/dennis/WorkOrderTracker/myenv/bin/activate
source  /home/dennis/WorkOrderTracker/.export
(cd  /home/dennis/WorkOrderTracker;gunicorn --config gunicornconfig.py 'app:create_app()' &)
