### youdao_share
搭配Hexo，用有道云协作的群共享里面的Markdown来写blog.  
将此脚本放在hexo blog目录下，用crontab自动检查同步然后生成静态资源.

#### 安装
```bash
$ cd ~/blog
$ git clone git@github.com:wuxc/youdao_share.git sync
```

#### 配置
- 在有道云协作建个群，共享一个文件夹，记下gid和共享token
- 修改sync\_youdao.py，填入gid和token, 如果没check到hexo根目录下，需要额外配一下savedir
- 增加crontab，例如: ```*/45 * * * * wuxc flock -xn ~wuxc/blog/sync/lock sh ~wuxc/blog/sync/update.sh > ~wuxc/blog/sync/update.log 2>&1```
