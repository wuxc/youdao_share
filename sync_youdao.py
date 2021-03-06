#-*- encoding: utf-8 -*-

import os
import sys
import urllib
import requests
import json
import re
import traceback
import time

HERE = os.path.dirname(os.path.abspath(__file__))
USER_AGENT="Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36"

def get_group_share_file(gid, token, fileid, fname, version):
    ftype = fname.rsplit(".")[-1]
    if ftype == "md":
        furl = "/yws/api/group/%s/file/%s?method=download&version=%s&shareToken=%s" % (gid, fileid, version, token)
        headers = {
            "Referer":"http://note.youdao.com/%s/preview/?file=%s" % (ftype, urllib.quote(furl)), 
            "User-Agent":USER_AGENT, 
            "HOST":"note.youdao.com",
        }
        url = "http://note.youdao.com%s" % furl
        r = requests.get(url, headers=headers)
        if isinstance(r.text, unicode):
            return r.text.encode("utf8", "ignore")
        return r.text

    elif ftype == "table":
        url = "http://note.youdao.com/yws/api/group/%s/preview/%s?method=convert&shareToken=%s" % (gid, fileid, token)
        headers = {
            "Referer":"http://note.youdao.com/groupshare/web/file.html?token=%s&gid=%s" % (token, gid), 
            "User-Agent":USER_AGENT, 
            "HOST":"note.youdao.com",
        }
        r = requests.get(url, headers=headers)

        m = re.search("window.userId = \"(.*)\";", r.text)
        win_userid = m and m.groups()[0] or "" 
        m = re.search("window.token = \"(.*)\";", r.text)
        win_token = m and m .groups()[0] or "" 
        if not win_userid or not win_token:
            raise Exception("get temporary token failed: %s %s" % (win_userid, win_token))

        url = "http://note.youdao.com/table/api/group/%s/table/%s?token=%s&method=getContent&userId=%s" % (gid, fileid, win_token, win_userid)
        headers = {
            "Referer":"http://note.youdao.com/yws/api/group/%s/preview/%s?method=convert&shareToken=%s" % (gid, fileid, token), 
            "User-Agent":USER_AGENT, 
            "HOST":"note.youdao.com",
        }
        r = requests.get(url, headers=headers)
        if isinstance(r.text, unicode):
            return r.text.encode("utf8", "ignore")
        return r.text

    elif ftype == "note":
        url = "http://note.youdao.com/yws/api/group/%s/note/%s?method=get-content&shareToken=%s" % (gid, fileid, token)
        headers = {
            "Referer":"Referer:http://note.youdao.com/groupshare/web/file.html?token=%s&gid=%s" % (token, gid), 
            "User-Agent":USER_AGENT, 
            "HOST":"note.youdao.com",
        }
        r = requests.get(url, headers=headers)
        if isinstance(r.text, unicode):
            return r.text.encode("utf8", "ignore")
        return r.text

    else:
        raise Exception("unknown file type %s" % ftype)

def get_group_share(gid, token):
    url = "http://note.youdao.com/yws/api/group/%s/share/?method=get&shareToken=%s" % (gid, token)
    r = requests.get(url)
    data = json.loads(r.text)

    if data["fileModel"]["dir"]:
        path_strip_len = len(data["fileModel"]["name"])+1
    else:
        path_strip_len = 0

    ## 递归生成文件列表，可能会消耗比较长的时间
    files = {}
    def _walk(info, ppath=""):
        fileinfo = info["fileModel"]
        if fileinfo["dir"]:
            for child in info["children"]:
                if child["dir"]:
                    url = "http://note.youdao.com/yws/api/group/%s/share/?method=get&shareToken=%s&fileId=%s" % (gid, token, child["fileId"])
                    headers = {
                        "Referer":"http://note.youdao.com/groupshare/web/folder.html?token=%s&gid=%s&fileId=%s" % (gid, token, child["fileId"]),
                        "User-Agent":USER_AGENT, 
                        "HOST":"note.youdao.com",
                    }
                    r = requests.get(url, headers=headers)
                    d = json.loads(r.text)
                    _walk(d, "%s%s/" % (ppath, fileinfo["name"]))
                else:
                    fileid = str(child["fileId"])
                    path = "%s%s/%s" % (ppath, fileinfo["name"], child["name"])
                    path = path.lower().replace(" ", "_")[path_strip_len:]
                    files[fileid] = {
                        "fname": child["name"],
                        #"title": child["title"].rsplit(".", 1)[0],
                        "version" : child["version"],
                        "createtime" : child["createTime"],
                        "lastuptime" : child["lastUpdateTime"],
                        "path" : path,
                    }
        else:
            fileid = str(fileinfo["fileId"])
            path = "%s%s" % (ppath, fileinfo["name"])
            path = path.lower().replace(" ", "_")[path_strip_len:]
            files[fileid] = {
                "fname": fileinfo["name"],
                #"title": fileinfo["title"].rsplit(".", 1)[0],
                "version" : fileinfo["version"],
                "createtime" : fileinfo["createTime"],
                "lastuptime" : fileinfo["lastUpdateTime"],
                "path" : path,
            }
    
    _walk(data)
    return files

def add_post_meta(info):
    pass

def sync_blog_posts(gid, token, backup="posts.json", savedir="../source/_posts"):
    changed = False

    _get_dstpath = lambda p : os.path.abspath(os.path.join(HERE, savedir, p))

    current = {}
    if os.path.isfile(backup):
        with open(backup) as f:
            current = json.loads(f.read())

    latest = get_group_share(gid, token)
    for fileid, info in latest.iteritems():
        print "checking", fileid, fileid in current, info
        if fileid not in current or info["lastuptime"] > current[fileid]["lastuptime"]:
            try:
                path = _get_dstpath(info["path"])
                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                content = get_group_share_file(gid, token, fileid, info["fname"], info["version"])
                if "\n" in content:
                    firstline, content = content.split("\n", 1)
                else:
                    firstline, content = content, ""
                # add meta info for markdown files, for example:
                #    title: test
                #    date: 2016-02-25 07:07:38
                #    tags:
                #    ---
                meta = [
                    "title: %s" % firstline,
                    "date: %s" % time.strftime("%F %T", time.localtime(info["createtime"]/1000.)),
                    "tags: ",
                    "---\n",
                ]
                with open(path, "w") as f:
                    f.write("\n".join(meta))
                    f.write(content)
                changed = True
            except:
                print "sync %s failed %s" % (info["fname"], traceback.format_exc())
        else:
            print "file %s already up to date." % info["fname"]

        ## file has been moved
        if fileid in current and current[fileid]["path"] != info["path"]:
            path = _get_dstpath(info["path"])
            os.unlink(path)

    with open(backup, "w") as f:
        f.write(json.dumps(latest, indent=4))

    return changed

if __name__ == "__main__":
    #from pprint import pprint
    gid = "5170358"
    token = "6624F0A167EB4225A30B166C2755C903" ## should share a folder

    print "%s  %s %s  %s" % ("-"*15, "start sync at", time.ctime(), "-"*15)
    changed = sync_blog_posts(gid, token)
    sys.exit(not changed)
    print "%s  %s %s  %s" % ("-"*15, " done sync at", time.ctime(), "-"*15)
    print

