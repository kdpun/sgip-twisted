## sgip-twisted
> 报文解析和逻辑代码来自[orangle/sgip1.2](https://github.com/orangle/sgip1.2)和[ElegantCloud/fy_sgip4py](https://github.com/ElegantCloud/fy_sgip4py), 本项目只是基于前者的Twisted实现

#### API
##### 接收短信(Deliver)
本网关就收到Deliver消息，同步到业务处理系统
> - 配置conf.py的SYNC_URL
> - 用户发送短信到指定号码，网关接收到Deliver消息
> - 本网关将解包后的Deliver消息转发到指定业务处理系统

method: POST

param:

|name|usage|desc|
|:----|:----|:------|
|number|手机号码||
|content|短信内容||
|reserve|保留字段|存放linkId|

##### 发送短信(Submit)
业务处理系统通过调用此接口回复用户短信

host: /submit

method: GET/POST

param:

|name|usage|desc|
|:----|:--------|:------|
|UserNumber|手机号|手机号码前加“86”国别标志|
|MessageContent|短信内容||
|ServiceType|业务代码，由SP定义||
|MoMtFlag|引起MT消息的原因|0-MO点播引起的第一条MT消息;1-MO点播引起的非第一条MT消息;2-非MO点播引起的MT消息;3-系统反馈引起的MT消息。|
|FeeType|计费类型|见《联通在信网关连接和业务流程.doc》|
|FeeValue|收费值|单位为: 分|
|ChargeNumber|付费号码||
|Reserve|保留字段|存放linkId，要与Deliver消息对应|


#### 配置(conf.py)
```
# SP PARAM
SP_PARAM = {
    'host': '',            # smg地址
    'port': 8080,          # smg端口
    'corp_id': '',         # 企业号
    'username': '',        # 用户名
    'pwd': '',             # 密码
    'sp_number': '',       # sp代号
    'node_num': '',        # 通信节点编号, 参考3.3节, SP的编号规则: 3AAAAQQQQQ
}

# SMG PARAM
SMG_PARAM = {
    'username': 'openet',       # 用户名
    'pwd': 'openet',            # 密码
}

# deliver消息转发
SYNC_URL = 'http://127.0.0.1:8090/auto'

```
