#!/bin/bash
# Provides:          <XITORING>
# Description:       <Xitogent>
# chkconfig: 2345 20 80

SCRIPT="/usr/bin/python2 /usr/bin/xitogent start -c /etc/xitogent/xitogent.conf"
RUNAS=root

PIDFILE=/var/run/xitogent.pid
PIDNAME=xitogent.pid
LOGFILE=/var/log/xitogent.log

start() {
  if [ -f /var/run/$PIDNAME ] && kill -0 $(cat /var/run/$PIDNAME); then
    echo 'Service already running' >&2
    return 1
  fi
  echo 'Starting service…' >&2
  local CMD="$SCRIPT &> \"$LOGFILE\" & echo \$!"
  su -c "$CMD" $RUNAS > "$PIDFILE"
  echo 'Service started' >&2
}

stop() {
  if [ ! -f "$PIDFILE" ] || ! kill -0 $(cat "$PIDFILE"); then
    echo 'Service not running' >&2
    return 1
  fi
  echo 'Stopping service…' >&2
  kill -9 $(cat "$PIDFILE") && rm -rf "$PIDFILE"
  rm -rf /tmp/_MEI*
  echo 'Service stopped' >&2
}

status() {
	if [ -f /var/run/$PIDNAME ] && kill -0 $(cat /var/run/$PIDNAME); then
		echo -e "\e[32mXitogent is Running\e[0m"
		return 1
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
