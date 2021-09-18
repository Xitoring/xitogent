#!/bin/bash
# Provides:          <XITORING>
# Description:       <Xitogent>
# chkconfig: 2345 20 80

SCRIPT="/usr/bin/xitogent start -d -c /etc/xitogent/xitogent.conf"
RUNAS=root

PIDFILE=/var/run/xitogent.pid
PIDNAME=xitogent.pid
LOGFILE=/var/log/xitogent.log

start() {
  if [ -f /var/run/$PIDNAME ] && [ -s /var/run/$PIDNAME ]; then
    echo 'Service already running' >&2
    exit 0
  fi
  echo 'Starting service…' >&2
  local CMD="$SCRIPT &> /dev/null & echo \$!"
  su -c "$CMD" $RUNAS
  echo 'Service started' >&2
}

stop() {
        xitogent stop
}

status() {
        if [ -f /var/run/$PIDNAME ] && [ -s /var/run/$PIDNAME ]; then
                echo -e "\e[32mXitogent is Running\e[0m"
                exit 0
        else
                echo -e "\e[31mXitogent is not Running\e[0m"
        fi
}

case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  status)
    status
    ;;
  restart)
    stop
    start
    ;;
  *)
    echo "Usage: {start|stop|restart|status}"
esac
