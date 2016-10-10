#! /usr/bin/env python
# -*- coding: utf-8 -*-

# config of sgip


# SP PARAM
SP_PARAM = {
    'host': '',    # smg地址
    'port': 8080,               # smg端口
    'corp_id': '',         # 企业号
    'username': '',     # 用户名
    'pwd': '',            # 密码
    'sp_number': '',    # sp代号
    'node_num': '',   # 通信节点编号, 参考3.3节, SP的编号规则: 3AAAAQQQQQ
}

# SMG PARAM
SMG_PARAM = {
    'username': 'openet',       # 用户名
    'pwd': 'openet',            # 密码
}

# deliver消息转发
SYNC_URL = 'http://127.0.0.1:8090/auto'
