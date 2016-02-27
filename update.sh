#! /bin/bash

PATH=$PATH:/home/wuxc/.nvm/versions/node/v4.3.1/bin/

cd $(dirname $0)
python sync_youdao.py

if [ $? == 0 ]; then
    cd ..
    hexo clean
    hexo generate
    hexo deploy
fi
