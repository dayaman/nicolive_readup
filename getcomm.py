import http.cookiejar
import urllib.request
from time import sleep

import json 
import socket
import struct
import re
from bs4 import BeautifulSoup
from xml.dom import minidom
import sys
from voice import knockApi
import subprocess
import threading
import queue
import ctrl_sqlite

comm_q = queue.Queue()
is_readup = None

def main():
    global is_readup
    global comm_q

    with open('token.json') as f:
        df = json.load(f)

    # 放送のIDをいれる
    lvno = input('Live IDを入力:')
    while ( is_readup != 'y' and is_readup != 'n'):
        is_readup = input('読み上げますか?(y/n):')
    
    # ニコ生にログインしてるブラウザからクッキー"user_session"の値を持ってきてsidに入れる
    sid=df['user_session']
    
    # 放送の情報を取得するurl。ここから、コメントを取得するサーバのアドレス,ポート番号と、スレッドidを取得する
    apistat_url="http://watch.live.nicovideo.jp/api/getplayerstatus?v=%s"
    
    # 取得時に設定するuser-agent
    uagent = "test test"
    
    # まずはアクセス時のクッキーを作る(user_sessionを設定するだけ)
    cj = http.cookiejar.CookieJar()
    ck = http.cookiejar.Cookie(version=0, name='user_session', value=sid, port=None,port_specified=False, domain='.live.nicovideo.jp', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
    cj.set_cookie(ck)
    opener =  urllib.request.build_opener( urllib.request.HTTPCookieProcessor(cj))
    
    # user-agent設定
    opener.addheaders = [('User-agent', uagent)]
    
    # url生成してアクセス
    target_url = apistat_url % lvno
    print(target_url)
    r = opener.open(target_url)
    data = r.read() #GETのレスポンス取得(xml形式)
    r.close()
    
    # XMLのデータからサーバのアドレス,ポート番号と、スレッドidを取り出す
    doc = minidom.parseString(data)
    child = doc.getElementsByTagName('getplayerstatus')[0]
    if child.getElementsByTagName('ms'):
        mstag = child.getElementsByTagName('ms')[0]
        addr = mstag.getElementsByTagName('addr')[0].firstChild.data.strip()
        port = mstag.getElementsByTagName('port')[0].firstChild.data.strip()
        threadid = mstag.getElementsByTagName('thread')[0].firstChild.data.strip()
    
    # ソケット生成し、取得したアドレス、ポートで接続
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((addr, int(port)))
    
    # スレッドIDを埋め込んだ文字列を送信(末尾に"0"を付ける)
    sd = '<thread thread="{}" version="20061206" res_from="-1"/>'.format(threadid)
    print(sock.send(sd.encode()))
    print(sock.send(struct.pack('b',0)))

    # 一回目の受信データは無視
    data = sock.recv(2048)
    # 読み上げの起動
    if is_readup == 'y':
        re_th = threading.Thread(target=readup)
        re_th.start()
    # コメントを取得して表示
    while True:
        data = sock.recv(2048)
        come = BeautifulSoup(data.decode(), features="html.parser")
        msg = come.chat.string
        index = msg.rfind("@") #ケツから検索
        if msg[0] == "/":
            continue
        if come.chat.get('anonymity') == '1':
            user_name = ""
            disp_name = "名無しさん"
        else:
            user_name = insert_kote(come.chat.get('user_id'), msg[index+1:]) if index != -1 else get_name(come.chat.get('user_id'))
            disp_name = user_name
            

        print('{}:{}'.format(msg, disp_name))
        if is_readup == 'y':
            comm_q.put("{}、{}".format(msg, user_name))

def readup():
    global comm_q
    while True:
        while not comm_q.empty():
            try:
                knockApi(comm_q.get(), "maki", "nico")
                cmd = 'play ./sound/nico/msg.wav'
                subprocess.run(cmd, stdout = subprocess.DEVNULL,stderr = subprocess.DEVNULL, shell=True)
            except:
                pass
        sleep(1)

def get_name(user_id):
    user_name = ctrl_sqlite.search(user_id)
    if user_name == None:
        user_page = urllib.request.urlopen('https://www.nicovideo.jp/user/' + user_id)
        user_soup = BeautifulSoup(user_page, features="html.parser")
        user_name = user_soup.find('meta', property="profile:username").get("content")
        ctrl_sqlite.insert(user_id, user_name)
    else:
        user_name = user_name[0]

    return user_name

def insert_kote(user_id, kotehan):
    ctrl_sqlite.insert(user_id, kotehan)
    return kotehan


if __name__ == '__main__':
    main()
