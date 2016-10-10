# encoding: utf-8

from twisted.web import client
from twisted.internet.protocol import Factory, ClientFactory, ReconnectingClientFactory
from twisted.internet import reactor
from twisted.application import internet, service
from twisted.python.log import ILogObserver, FileLogObserver
from twisted.python.logfile import DailyLogFile
from twisted.web import resource, server
from SgipMsg import *
from .utils import LogServer, DeferredQueue, RestResource
from SgipProtocol import Sgip
from conf import SP_PARAM, SMG_PARAM, SYNC_URL


class SgipDeliverFactory(Factory):

    def __init__(self, logServer):
        self.p = Sgip(mode='server')
        self.logServer = logServer

    def buildProtocol(self, addr):
        self.p.factory = self
        return self.p

    # sync deliver message to bussiess system
    def sync(self, number, content, reserve):
        url = SYNC_URL
        print 'in sync'

        number = number.replace('\x00', '')
        self.logServer.write_log(number + ',' + content + ',' + reserve)

        print 'number', number
        print 'content', content
        print 'reserve', reserve

        param = {'number': number, 'content': content, 'reserve': reserve}
        RestResource(url).post(**param)


class SgipSubmitFactory(ReconnectingClientFactory):

    maxDelay = 10

    def __init__(self, logServer, SubmitQueue):
        self.p = Sgip(mode='client')
        self.status = 'Unbind'
        self.isConnected = False
        self.logServer = logServer
        self.SubmitQueue = SubmitQueue

        # 插入wait队列等待推送消息
        self.getSubmit()

    def buildProtocol(self, addr):
        self.p.factory = self
        self.resetDelay()
        return self.p

    def startedConnecting(self, connector):
        print('Started to connect.')
        self.isConnected = True

    def clientConnectionLost(self, connector, reason):
        print('Lost connection.  Reason:', reason)
        self.isConnected = False
        self.status = 'Unbind' 
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed. Reason:', reason)
        self.isConnected = False
        self.status = 'Unbind' 
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    # submit queue handle flow
    def getSubmit(self):
        print '==============getSubmit======================\n'
        if self.SubmitQueue.getpendinglength() == 0 and self.status == 'Bind':
            self.p.unbind()
            self.p.transport.loseConnection()

        dif = self.SubmitQueue.get()
        dif.addCallback(self.submitHandler)
        dif.addErrback(self.getSubmitError)

    def getSubmitError(self, err):
        print '==============getSubmitError=================\n'
        print err
        self.getSubmit()

    def submitHandler(self, *args):
        print '==============getSubmitHandler=================\n'

        ChargeNumber = args[0]["ChargeNumber"]
        UserNumber = args[0]["UserNumber"]
        ServiceType = args[0]["ServiceType"]
        FeeType = args[0]["FeeType"]
        FeeValue = args[0]["FeeValue"]
        MoMtFlag = args[0]["MoMtFlag"]
        MessageContent = args[0]["MessageContent"]
        Reserve = args[0]["Reserve"]

        self.logServer.write_log(ChargeNumber + ',' + UserNumber + ',' + ServiceType + ',' + FeeType + ',' + FeeValue + ',' + MoMtFlag + ',' + MessageContent + ',' + Reserve)
      
        if self.isConnected: 
            if self.status == 'Unbind':
                self.p.bind()
            self.p.submit(ChargeNumber, UserNumber, ServiceType, FeeType, FeeValue, MoMtFlag, MessageContent, Reserve)
            def get():
                self.getSubmit()
            reactor.callLater(1, get)
        else:
            print 'Not Connected!! Re-put into SubmitQueue.'
            def reput(args):
                self.SubmitQueue.put(args[0])
                self.getSubmit()
            reactor.callLater(3, reput, args)
        

class SubmitApi(resource.Resource):

    def __init__(self, SubmitQueue):
        resource.Resource.__init__(self)
        self.SubmitQueue = SubmitQueue

    def render_POST(self, request):
        args = request.args

        UserNumber = args["UserNumber"][0]
        MessageContent = args["MessageContent"][0]
        ServiceType = args["ServiceType"][0]
        MoMtFlag = args["MoMtFlag"][0]
        FeeType = args["FeeType"][0]
        FeeValue = args["FeeValue"][0]
        ChargeNumber = args["ChargeNumber"][0]
        Reserve = args["Reserve"][0]

        self.SubmitQueue.put({
            'UserNumber': UserNumber,
            'MessageContent': MessageContent,
            'ServiceType': ServiceType,
            'MoMtFlag': MoMtFlag,
            'FeeType': FeeType,
            'FeeValue': FeeValue,
            'ChargeNumber': ChargeNumber,
            'Reserve': Reserve,
        })

        print 'wait:', self.SubmitQueue.getwaitinglength()
        print 'pending:', self.SubmitQueue.getpendinglength()
        return 'ok'

    def render_GET(self, request):
        args = request.args

        UserNumber = args["UserNumber"][0]
        MessageContent = args["MessageContent"][0]
        ServiceType = args["ServiceType"][0]
        MoMtFlag = args["MoMtFlag"][0]
        FeeType = args["FeeType"][0]
        FeeValue = args["FeeValue"][0]
        ChargeNumber = args["ChargeNumber"][0]
        Reserve = args["Reserve"][0]

        self.SubmitQueue.put({
            'UserNumber': UserNumber,
            'MessageContent': MessageContent,
            'ServiceType': ServiceType,
            'MoMtFlag': MoMtFlag,
            'FeeType': FeeType,
            'FeeValue': FeeValue,
            'ChargeNumber': ChargeNumber,
            'Reserve': Reserve,
        })

        print 'wait:', self.SubmitQueue.getwaitinglength()
        print 'pending', self.SubmitQueue.getpendinglength()
        return 'ok'


class RootResource(resource.Resource):
    def __init__(self, SubmitQueue):
        resource.Resource.__init__(self)
        self.SubmitQueue = SubmitQueue
        self.putChild('submit', SubmitApi(SubmitQueue))


_logfilename = './log/twistd.log'
_logfile = DailyLogFile.fromFullPath(_logfilename)

SubmitQueue = DeferredQueue()
submit_log = LogServer('./log/submit.log')
deliver_log = LogServer('./log/deliver.log')

application = service.Application('SgipGateway', uid=0, gid=0)
serviceCollection = service.IServiceCollection(application)

application.setComponent(ILogObserver, FileLogObserver(_logfile).emit)

deliver = internet.TCPServer(8088, SgipDeliverFactory(deliver_log))
deliver.setServiceParent(serviceCollection)

submit = internet.TCPClient(SP_PARAM['host'], SP_PARAM['port'], SgipSubmitFactory(submit_log, SubmitQueue))
submit.setServiceParent(serviceCollection)
submit_api = internet.TCPServer(8089, server.Site(RootResource(SubmitQueue)))
submit_api.setServiceParent(serviceCollection)
