#! /bin/bash

workdir=$(dirname $0)

python $workdir/sync_youdao.py > $workdir/update.log 2>&1

