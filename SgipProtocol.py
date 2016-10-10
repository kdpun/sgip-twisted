# encoding: utf-8

from twisted.internet.protocol import Protocol
from SgipMsg import *
from binascii import hexlify
import datetime
import threading
from conf import SP_PARAM, SMG_PARAM


count = 0
lock = threading.Lock()


def get_count():
    lock.acquire()
    try:
        global count
        count += 1
        if count > 99999:
            count = 0
    finally:
        lock.release()
    return count


class Sgip(Protocol):

    def __init__(self, mode):
        self._host = SP_PARAM['host']
        self._port = SP_PARAM['port']
        self._corp_id = SP_PARAM['corp_id']
        self._username = SP_PARAM['username']
        self._pwd = SP_PARAM['pwd']
        self._sp_number = SP_PARAM['sp_number']
        self._node_num = SP_PARAM['node_num']

        self._smg_username = SMG_PARAM['username']
        self._smg_pwd = SMG_PARAM['pwd']

        self._mode = mode


    def dataReceived(self, data):
        print 'recv data:', hexlify(data)

        size = len(data)

        head = data[:20]
        body = data[20:]

        receivedHeader = SGIPHeader()
        receivedHeader.unpack(head)
        print('Message Length: {0}'.format(receivedHeader.MessageLength))
        print('Command ID: {0}'.format(receivedHeader.CommandID))
        print('Sequence Number: {0}'.format(receivedHeader.SequenceNumber))

        # Command ID 不存在
        if receivedHeader.CommandID not in CommandID.__dict__.values():
            return

        command = dict((v, k) for k, v in CommandID.__dict__.iteritems())[receivedHeader.CommandID]

        if command == 'BIND':
            self.bind_handler(head, body)
        elif command == 'BIND_RESP':
            self.bind_resp_handler(head, body)
        elif command == 'UNBIND':
             self.unbind_handler(head, body)
        elif command == 'UNBIND_RESP':
            self.unbind_resp_handler(head, body)
        elif command == 'SUBMIT_RESP':
            self.submit_resp_handler(head, body)
        elif command == 'DELIVER':
            self.deliver_handler(head, body)


    def gen_seq_number(self):
        """
        :doc 序列号的定义,参考3.4节的内容
        :return sqe_num
        """
        seq_num1 = self._node_num
        seq_num2 = datetime.datetime.now().strftime('%m%d%H%M%S')
        seq_num3 = get_count()
        return [seq_num1, seq_num2, seq_num3]


    def bind_handler(self, head, body):
        """
        :doc 绑定,Deliver时由SMG发起
        """
        print('Bind(SMG TO SP)')

        respHeader = SGIPHeader()
        respHeader.unpack(head)
        bindMsg = SGIPBind()
        bindMsg.unpackBody(body)
 
       	print 'login type:', bindMsg.LoginType
        print 'login name:', bindMsg.LoginName
        print 'login pwd:', bindMsg.LoginPassword

        if respHeader.CommandID == SGIPBind.ID:
            print 'smg bind sp success'
            self.bind_resp()
        else:
            print 'smg bind sp failed'


    def unbind_handler(self, head, body):
        """
        :doc 解除绑定,Deliver时由SMG发起
        """
        print('Unbind(SMG TO SP)')

        respHeader = SGIPHeader()
        respHeader.unpack(head)
        unbindMsg = SGIPUnbind()
        unbindMsg.unpackBody(body)

        if respHeader.CommandID == SGIPUnbind.ID:
            print 'smg unbind sp success'
            self.unbind_resp()
        else:
            print 'smg unbind sp failed'


    def bind_resp(self):
        """
        :doc 绑定响应,Deliver时由SP返回
        """
        print 'BindResp(SP TO SMG)'

        bindRespMsg = SGIPBindResp()
        header = SGIPHeader(
            SGIPHeader.size() + bindRespMsg.size(),
            SGIPBindResp.ID,
            self.gen_seq_number()
        )
        bindRespMsg.header = header
        raw_data = bindRespMsg.pack()

        self.transport.write(raw_data)


    def unbind_resp(self):
        """
        :doc 解除绑定响应,Deliver时由SP返回
        """
        print 'unbindResp(SP TO SMG)'

        unbindRespMsg = SGIPUnbindResp()
        header = SGIPHeader(
            SGIPHeader.size() + unbindRespMsg.size(),
            SGIPUnbindResp.ID,
            self.gen_seq_number()
        )
        unbindRespMsg.header = header
        raw_data = unbindRespMsg.pack()

        self.transport.write(raw_data)

        # self.transport.loseConnection()


    def bind(self):
        """
        :doc 绑定,Submit时由SP发起
        """
        print('Bind(SP TO SMG)')

        bindMsg = SGIPBind(1, self._username, self._pwd)
        header = SGIPHeader(
            SGIPHeader.size() + bindMsg.size(),
            SGIPBind.ID,
            self.gen_seq_number()
        )
        bindMsg.header = header
        raw_data = bindMsg.pack()

        self.transport.write(raw_data)


    def bind_resp_handler(self, head, body):
        """
        :doc 绑定响应,Submit时由SMG返回
        """
        print('Bind Resp(SMG TO SP)')
        if head == '':
            return False

        respHeader = SGIPHeader()
        respHeader.unpack(head)
        bindRespMsg = SGIPBindResp()
        bindRespMsg.unpackBody(body)

        print('BindRespMsg Result: {0}'.format(bindRespMsg.Result))

        if respHeader.CommandID == SGIPBindResp.ID and bindRespMsg.Result == 0:
            print 'sp bind smg success'
            self.factory.status = 'Bind'
        else:
            print 'sp bind smg failed'
            self.factory.status = 'Unbind'


    def unbind(self):
        """
        :doc 解除绑定,Submit时由SP发起
        """
        print('Unbind(SP TO SMG)')

        unbindMsg = SGIPUnbind()
        header = SGIPHeader(
            SGIPHeader.size() + unbindMsg.size(),
            SGIPUnbind.ID,
            self.gen_seq_number()
        )
        unbindMsg.header = header
        raw_data = unbindMsg.pack()
        
        self.transport.write(raw_data)


    def unbind_resp_handler(self, head, body):
        """
        :doc 解除绑定响应,Submit时由SMG返回
        """
        print('Unbind Resp(SMG TO SP)')

        self.factory.status = 'Unbind'

        # self.transport.loseConnection()


    def submit(self, charge_number, user_number, service_type, fee_type, fee_value, morelateto_mt_flag, msg_content, reserve):
        """
        :doc 提交短消息,由SP发起
        """
        print('Submit(SP TO SMG)')

        msg_content = msg_content.decode('utf-8').encode('gbk')
        submitMsg = SGIPSubmit(
            sp_number=self._sp_number,
            charge_number=charge_number,
            user_number=user_number,
            corp_id=self._corp_id,
            service_type=service_type,
            fee_type=int(fee_type),
            fee_value=fee_value,
            morelateto_mt_flag=int(morelateto_mt_flag),
            msg_len=len(msg_content),
            msg_content=msg_content,
            reserve=reserve
        )
        header = SGIPHeader(
            SGIPHeader.size() + submitMsg.mySize(),
            SGIPSubmit.ID,
            self.gen_seq_number()
        )
        submitMsg.header = header
        raw_data = submitMsg.pack()

        self.transport.write(raw_data)


    def submit_resp_handler(self, head, body):
        """
        :doc 提交短消息响应,由SMG返回
        """
        print('Submit Resp(SMG TO SP)')

        if head == '' or body == '':
            print('sms submit failed')
            return False

        respHeader = SGIPHeader()
        respHeader.unpack(head)
        submitRespMsg = SGIPSubmitResp()
        submitRespMsg.unpackBody(body)

        print('SubmitResp Result: {0}'.format(submitRespMsg.Result))

        if respHeader.CommandID == SGIPSubmitResp.ID and submitRespMsg.Result == 0:
            print('sms submitted ok')
        else:
            print('sms submit failed')


    def deliver_handler(self, head, body):
        """
        :doc 接收短信息,由SMG发起
        """
        print('Deliver(SMG TO SP)')

        respHeader = SGIPHeader()
        respHeader.unpack(head)

        deliverMsg = SGIPDeliver()
        deliverMsg.contentLength = respHeader.MessageLength - respHeader.size() - SGIPDeliver.size()
        deliverMsg.unpackBody(body)

        if respHeader.CommandID == SGIPDeliver.ID:
            print('sms deliver ok')
            print('User Number:', deliverMsg.UserNumber)
            print('Message Coding:', deliverMsg.MessageCoding)
            print('Message Content:', deliverMsg.MessageContent)
            print('Reserve:', str(deliverMsg.Reserve))

            self.deliver_resp()
            # 调用factory的sync方法,将deliver接受到的信息同步出去
            self.factory.sync(deliverMsg.UserNumber, deliverMsg.MessageContent, deliverMsg.Reserve)
        else:
            print('sms deliver failed')


    def deliver_resp(self):
        """
        :doc 接收短信息响应,由SP返回
        """
        print('Deliver Resp(SP TO SMG)')

        deliverRespMsg = SGIPDeliverResp()
        header = SGIPHeader(
            SGIPHeader.size() + deliverRespMsg.size(),
            SGIPBind.ID,
            self.gen_seq_number()
        )
        deliverRespMsg.header = header
        raw_data = deliverRespMsg.pack()

        self.transport.write(raw_data)

