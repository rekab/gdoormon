#!/bin/bash

PIDFILE=/tmp/gdoormon.pid
set -e
dir=$(dirname $0)
cd $dir
if [ ! -d deps ] ; then
  echo '"deps" directory missing: check virtualenv setup' >2
  exit 1
fi
. deps/bin/activate

function is_running() {
  [ -f $PIDFILE ] && kill -0 $(cat $PIDFILE)
}

COMMAND="$1"
shift
FLAGS=$*

case $COMMAND in
status)
  if is_running ; then
    echo "process is alive as pid " $(cat $PIDFILE)
  else
    echo "process is dead"
  fi
  ;;
start)
  if is_running ; then
    echo "process is already running"
  else
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
