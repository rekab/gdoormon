#!/bin/bash

set -e
dir=$(dirname $0)
cd $dir
if [ ! -d deps ] ; then
  echo '"deps" directory missing: check virtualenv setup' >2
  exit 1
fi
. deps/bin/activate
deps/bin/twistd --pidfile=/tmp/gdoormon.pid -y $* $dir/main.py
