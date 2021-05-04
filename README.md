# wxbot

微信聊天记录自动存sqlite数据库，基于微信网页版。注意，Web版获取不到微信用户的微信ID，所得到的用户名/ID是仅当前会话有效的，因此只有根据备注名在数据库中识别用户比较靠谱。

项目fork自[@Urinx/WeixinBot](https://github.com/Urinx/WeixinBot)，我只是加了个存到sqlite的壳，感谢老哥的网页版微信API。

## 数据表结构
| 字段名 | 类型 | 说明 |
|  --   | --  | --   |
| msg_id| TEXT | 消息ID，结构为创建时间+原微信消息ID |
|create_time | INTEGER | 创建时间，Unix时间戳 |
| msg_type | INTEGER | 消息类型，1-文本，3-图片，34-语音，43-视频，0-其它 |
| content | TEXT | 消息的文本内容 |
| from_id | TEXT | 消息发送者ID（不是微信ID，没啥用），如果是来自群的消息此字段为空 |
| from_name | TEXT | 消息发送者的备注，没备注就昵称，如果是来自群的消息此字段为空 |
| from_nickname | TEXT | 消息发送者的昵称，如果是来自群的消息此字段为空 |
| to_id | TEXT | 接收者ID，如果是发送到群的消息此字段为空 |
| to_name | TEXT | 接收者备注，没备注就昵称，如果是发送到群的消息此字段为空 |
| to_nickname | TEXT | 接收者昵称，如果是发送到群的消息此字段为空 |
| group_id | TEXT | 如果是群消息则为群的ID否则为空，照样，没啥用 |
| group_name | TEXT | 如果是群消息则为群聊名称（应该吧🤣我不关注群消息），否则为空 |

消息里的图片等文件以消息ID存储于命令行参数给定的数据目录中，并根据年份划分子目录。

其它信息请参考[项目@Urinx/WeixinBot](https://github.com/Urinx/WeixinBot)。

## 使用
### 克隆仓库并安装python依赖
```shell
# 不适用win系统
git clone https://github.com/mattuylee/wxbot.git
cd wxbot
python3 -m venv ./venv
source ./venv/bin/activate
pip3 install -r ./requirements.txt
```

### 运行
`python ./main.py -f <DB_FILE> -d <DATA_DIR>`
其中`DB_FILE`是sqlite数据库文件路径，`DATA_DIR`是图片视频等数据的存储目录。

支持sqlcipher加密，程序启动会要求输入密码，如不需要加密可留空直接回车。注意，以后每次启动必须输入相同的密码。暂不支持修改密码，可自行安装sqlcipher打开数据库修改密码。

未加密数据库可直接通过sqlite3打开，加密数据库需要sqlcipher才能打开。程序只负责记录数据，没有读取能力。

### 其它
关于表情包，如果是从表情商店里添加的表情包网页版微信是获取不到的，为了保护创作者的权益。这倒是可以理解。

如果发现无法登录先试试在浏览器登录网页版微信，有可能是腾讯为了“安全”限制了你的微信帐号在网页登录。

最后，祝腾讯早点倒闭。
