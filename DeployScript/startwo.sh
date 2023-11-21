#!/bin/sh
### BEGIN INIT INFO
# Provides:          console-setup.sh
# Required-Start:    $remote_fs
# Required-Stop:
# Should-Start:      console-screen kbd
# Default-Start:     2 3 4 5
# Default-Stop:
# X-Interactive:     true
# Short-Description: Set console font and keymap
### END INIT INFO

    case "$1" in
        start)
        /home/dennis/startwork.sh
    esac
