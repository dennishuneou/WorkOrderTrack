#!/bin/bash
sudo mount -t cifs -w -o username=dennis.hu -o password=LuFZ8*id //192.168.62.100/Production/WorkOrderDatabaseBackup /home/neousys/databasebackup
sudo  /home/neousys/WorkOrderTracker/databasebackupscript/pg_rotated.sh

