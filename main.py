import argparse
import getpass
import logging
import sys
import os
from weixin import WebWeixin
from sqlcipher3 import dbapi2 as sqlite


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--db-file", required=True, help="数据库文件")
    parser.add_argument("-d", "--data-dir",required=True, help="文件存储目录")
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

    def handleMsg(self, r):
        for msg in r['AddMsgList']:
            msgID = msg['MsgId']
            msgType = msg['MsgType']
            sql = "INSERT INTO msg (\
                msg_id,\
                create_time,\
                msg_type,\
                content,\
                from_id,\
                from_name,\
                from_nickname,\
                to_id,\
                to_name,\
                to_nickname,\
                group_id,\
                group_name\
            ) VALUES (\
                :msg_id,\
                :create_time,\
                :msg_type,\
                :content,\
                :from_id,\
                :from_name,\
                :from_nickname,\
                :to_id,\
                :to_name,\
                :to_nickname,\
                :group_id,\
                :group_name\
            )"
            params = {
                "msg_id": msgID,
                "create_time": msg['CreateTime'],
                "msg_type": msgType,
                "content": None,
                "from_id": msg['FromUserName'],
                "from_name": self.getUserRemarkName(msg['FromUserName']),
                "from_nickname": self.getUserNickName(msg['FromUserName']),
                "to_id": msg['ToUserName'],
                "to_name": self.getUserRemarkName(msg['ToUserName']),
                "to_nickname": self.getUserNickName(msg['ToUserName']),
                "group_id": None,
                "group_name": None
            }
            # 过滤特殊帐号消息
            if msg['FromUserName'] in self.SpecialUsers or msg['ToUserName'] in self.SpecialUsers:
                continue
            if msgType == 1:
                params['content'] = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
            elif msgType == 3:
                params['content'] = "[图片](%s)" % msgID
                self.webwxgetmsgimg(msgID)
            elif msgType == 34:
                params['content'] = "[语音](%s)" % msgID
                self.webwxgetvoice(msgID)
            elif msgType == 43:
                params['content'] = "[视频](%s)" % msgID
                self.webwxgetvideo(msgID)
            elif msgType == 62:
                params['msg_type'] = 43
                params['content'] = "[小视频](%s)" % msgID
                self.webwxgetvideo(msgID)
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
                    params['content'] = "[动画表情](%s)" % msgID
                    self.webwxgetmsgimg(msgID)
            elif msgType == 49:
                params['msg_type'] = 0
                params['content'] = "[链接：%s](%s)" % (msg['FileName'], msg['Url'])
            elif (50, 51, 52, 53, 9999, 10000, 10002).index(msgType) >= 0:
                continue
            else:
                params['msg_type'] = 0
                params['content'] = ""
                continue
            # 群消息
            if msg['FromUserName'][:2] == '@@':
                if ":<br/>" in content:
                    [people, content] = msg['Content'].split(':<br/>', 1)
                    params['group_name'] = self.getUserRemarkName(msg['FromUserName'])
                    params['from_id'] = people
                    params['from_name'] = self.getUserRemarkName(people)
                    params['to_id'] = params['to_name'] = params['to_nickname'] = None
            elif msg['ToUserName'][:2] == '@@':
                params['group_name'] = self.getUserRemarkName(msg['ToUserName'])
                params['from_id'] = self.User['UserName']
                params['from_name'] = self.User['NickName']
                params['to_id'] = params['to_name'] = params['to_nickname'] = None
            conn.execute(sql, params)
            conn.commit()


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
            from_id TEXT,\
            from_name TEXT,\
            from_nickname TEXT,\
            to_id TEXT,\
            to_name TEXT,\
            to_nickname TEXT,\
            group_id TEXT,\
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


if sys.stdout.encoding == 'cp936':
    sys.stdout = UnicodeStreamFilter(sys.stdout)

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    if not sys.platform.startswith('win'):
        import coloredlogs
        coloredlogs.install(level='INFO')
    wxbot = WXBot()
    wxbot.saveFolder = dataDir
    wxbot.start()
