cd $(dirname $0)
status=0
for test in */test_*.py ; do 
  trial $test || status=$(($status + 1))
done

if [ $status -ne 0 ] ; then
  echo FAIL 1>&2
  exit $status
fi
