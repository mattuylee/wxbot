#!/usr/bin/env python3
# coding: utf-8
import argparse
import getpass
import logging
import sys
import time
import os
from weixin import WebWeixin
from sqlcipher3 import dbapi2 as sqlite


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--db-file', required=True, help='数据库文件')
    parser.add_argument('-d', '--data-dir',required=True, help='文件存储目录')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()
    return args


class WXBot(WebWeixin):
    def getUserNickName(self, id):
        if id == self.User['UserName']:
            return self.User['NickName']
        for member in self.ContactList:
            if member['UserName'] == id:
                return member['NickName']
        return None

    def composeMessageID(self, msgID, timestamp):
        return time.strftime('%Y%m%d%H%M%S', time.localtime(timestamp)) + msgID

    def saveMessageImage(self, msgid, composedID):
        url = self.base_uri + \
            '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url, 'webwxgetmsgimg')
        return self.saveFile(composedID[:4], composedID + '.jpg', data)

    def saveVoice(self, msgid, composedID):
        url = self.base_uri + \
            '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url, api='webwxgetvoice')
        return self.saveFile(composedID[:4], composedID + '.mp3', data)

    def saveVideo(self, msgid, composedID):
        url = self.base_uri + \
            '/webwxgetvideo?msgid=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url, api='webwxgetvideo')
        return self.saveFile(composedID[:4], composedID + '.mp4', data)

    def saveFile(self, subdir, filename, data):
        if data == '':
            return False
        dirName = os.path.join(dataDir, subdir)
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        fn = os.path.join(dirName, filename)
        with open(fn, 'wb') as f:
            f.write(data)
            f.close()
        return True

    def handleMsg(self, r):
        if self.DEBUG:
            print("处理消息, NewMessageCount =", r['AddMsgCount'])
        for msg in r['AddMsgList']:
            msgID = msg['MsgId']
            composedID = self.composeMessageID(msgID, msg['CreateTime'])
            msgType = msg['MsgType']
            if msg['FromUserName'] in self.SpecialUsers or msg['ToUserName'] in self.SpecialUsers:
                # 过滤特殊帐号消息
                continue
            elif msgType in (50, 51, 52, 53, 9999):
                #无用消息
                continue
            sql = "INSERT INTO msg (\
                msg_id,\
                create_time,\
                msg_type,\
                content,\
                from_name,\
                from_nickname,\
                to_name,\
                to_nickname,\
                group_name\
            ) VALUES (\
                :msg_id,\
                :create_time,\
                :msg_type,\
                :content,\
                :from_name,\
                :from_nickname,\
                :to_name,\
                :to_nickname,\
                :group_name\
            )"
            params = {
                "msg_id": composedID,
                "create_time": msg['CreateTime'],
                "msg_type": msgType,
                "content": None,
                "from_name": self.getUserRemarkName(msg['FromUserName']),
                "from_nickname": self.getUserNickName(msg['FromUserName']),
                "to_name": self.getUserRemarkName(msg['ToUserName']),
                "to_nickname": self.getUserNickName(msg['ToUserName']),
                "group_name": None
            }
            if msg['FromUserName'] == self.User['UserName']:
                params['from_name'] = '_self'
            elif msg['ToUserName'] == self.User['UserName']:
                params['to_name'] = '_self'
            if msg['FromUserName'][:2] == '@@':
                # 群消息
                if ":<br/>" in content:
                    [people, content] = msg['Content'].split(':<br/>', 1)
                    params['group_name'] = self.getUserRemarkName(msg['FromUserName'])
                    params['from_name'] = self.getUserRemarkName(people)
                    params['to_name'] = params['to_nickname'] = None
            elif msg['ToUserName'][:2] == '@@':
                # 发送的群消息
                params['group_name'] = self.getUserRemarkName(msg['ToUserName'])
                params['from_name'] = self.User['NickName']
                params['to_name'] = params['to_nickname'] = None
            if msgType == 1:
                # 文字消息
                params['content'] = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
            elif msgType == 3:
                params['content'] = "[图片](%s)" % composedID
                self.saveMessageImage(msgID, composedID)
            elif msgType == 34:
                params['content'] = "[语音](%s)" % composedID
                self.saveVoice(msgID, composedID)
            elif msgType == 43:
                params['content'] = "[视频](%s)" % composedID
                self.saveVideo(msgID, composedID)
            elif msgType == 62:
                params['msg_type'] = 43
                params['content'] = "[小视频](%s)" % composedID
                self.saveVideo(msgID, composedID)
            elif msgType == 42:
                params['msg_type'] = 0
                params['content'] = "[名片](%s)" % msg['RecommendInfo']['NickName']
            elif msgType == 47:
                if msg['HasProductId'] == 1:
                    # 有版权的表情包，无法在Web端查看
                    params['msg_type'] = 0
                    params['content'] = "[表情包图片]"
                else:
                    params['msg_type'] = 3
                    params['content'] = "[动画表情](%s)" % composedID
                    self.saveMessageImage(msgID, composedID)
            elif msgType == 49:
                params['msg_type'] = 0
                params['content'] = "[链接：%s](%s)" % (msg['FileName'], msg['Url'])
            elif msgType == 10000:
                params['msg_type'] = 0
                params['content'] = "[系统消息](%s)" % (msg['Content'])
            elif msgType == 10002:
                params['msg_type'] = 0
                params['content'] = "[系统消息](%s撤回了一条消息)" % params['from_name']
            else:
                params['msg_type'] = 0
                params['content'] = "[未识别消息]" + msg['Content']
            conn.execute(sql, params)
            conn.commit()


if __name__ == '__main__':
    if sys.stdout.encoding == 'cp936':
        sys.stdout = UnicodeStreamFilter(sys.stdout)

    logger = logging.getLogger(__name__)
    if not sys.platform.startswith('win'):
        import coloredlogs
        coloredlogs.install(level='INFO')

    args = parse_args()
    dataDir = args.data_dir
    if not os.access(os.path.dirname(args.db_file), os.X_OK) and not os.access(args.db_file, os.W_OK):
        print("无法创建或打开数据库文件")
        exit()
    elif not os.access(dataDir, os.X_OK):
        print("数据目录不存在或权限不足")
        exit()
    conn = sqlite.connect(args.db_file)
    while True:
        try:
            passwd = getpass.getpass("输入数据库密码：")
            if passwd != '':
                conn.execute("PRAGMA KEY = %s" % passwd)
            conn.execute("CREATE TABLE IF NOT EXISTS msg (\
                msg_id TEXT NOT NULL,\
                create_time INTEGER NOT NULL,\
                msg_type INTEGER NOT NULL,\
                content TEXT,\
                from_name TEXT,\
                from_nickname TEXT,\
                to_name TEXT,\
                to_nickname TEXT,\
                group_name TEXT\
            );")
            break
        except sqlite.DatabaseError as e:
            if 'file is not a database' in e.args:
                print("密码错误，请重试")
            else:
                print("打开数据库失败", e)
        except KeyboardInterrupt:
            exit(1)
        except Exception as e:
            print("打开数据库失败", e)
            exit(1)
    wxbot = WXBot()
    wxbot.DEBUG = args.debug
    wxbot.saveFolder = dataDir
    wxbot.start()
