#! /bin/bash

cd $(dirname $0)
python sync_youdao.py

cd ..
hexo clean
hexo generate
hexo deploy
