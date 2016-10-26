#! /bin/sh -x

set -e
spectool -S *.spec | cut -d' ' -f2 \
    | grep -E -e 'postgresql-.*\.tar\.*' -e 'postgresql.*\.pdf' | sort | \
while read line
do
    base=`basename "$line"`
    md5sum "$base"
done
