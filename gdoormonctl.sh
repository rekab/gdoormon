#!/bin/bash

set -e
dir=$(dirname $0)
PIDFILE=$dir/gdoormon.pid

cd $dir
if [ ! -d deps ] ; then
  echo '"deps" directory missing: check virtualenv setup' >2
  exit 1
fi
. deps/bin/activate

function is_running() {
  if [ -f $PIDFILE ] ; then 
    if kill -0 $(cat $PIDFILE) ; then
      return 0
    else
      echo "pidfile $PIDFILE exists but process is not alive" 1>&2
      return 1
    fi
  fi
  return 1
}

COMMAND="$1"
shift
FLAGS=$*

case $COMMAND in
status)
  if is_running ; then
    echo -n "process is alive as pid "
    cat $PIDFILE
  else
    echo "process is not running"
  fi
  ;;
start)
  if is_running ; then
    echo "process is already running"
  else
    set -x
    deps/bin/twistd --pidfile=$PIDFILE -y $FLAGS $dir/main.py
  fi
  ;;
stop)
  if is_running ; then
    set -x
    kill $(cat $PIDFILE)
  else
    echo "process is not running"
    exit 1
  fi
  ;;
esac
