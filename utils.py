# encoding: utf-8
from twisted.internet import defer
from twisted.web import client
import urllib
import os
import datetime
import time


class DeferredQueue(object):

    def __init__(self):
        """
        @summary: defer 队列。waiting 队列内的是deferred对象。
        """
        # It would be better if these both used collections.deque (see comments section below).
        self.waiting = []  # Deferreds that are expecting an object
        self.pending = []  # Objects queued to go out via get.

    def put(self, obj):
        if self.waiting:
            self.waiting.pop(0).callback(obj)
        else:
            self.pending.append(obj)

    def get(self):
        if self.pending:
            return defer.succeed(self.pending.pop(0))
        else:
            d = defer.Deferred()
            self.waiting.append(d)
            return d

    def getwaitinglength(self):
        return len(self.waiting)

    def getpendinglength(self):
        return len(self.pending)


class LogServer(object):

    def __init__(self, filename):
        self.filename = filename
        self.logger = open(filename, 'a')

    def checkLogDate(self, filename):
        today = datetime.date.today()
        info = os.stat(filename)
        last_modify_date = datetime.date.fromtimestamp(info.st_mtime)
        if today == last_modify_date:
            return 0
        else:
            return 1

    def write_log(self, logdata):
        result = self.checkLogDate(self.filename)
        if result == 1:
            self.rename()
        time0 = (time.strftime("%Y-%m-%d %H:%M:%S,"))
        data = time0 + logdata + '\n'
        self.logger.write(data)
        self.logger.flush()

    def rename(self):
        filename = self.filename
        self.logger.close()
        if os.path.isfile(filename):
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            oldfilename = filename+'.'+str(yesterday)
            os.rename(filename, oldfilename)
            self.logger = open(self.filename, 'a')


class RestResource(object):
    def __init__(self, uri):
        self.uri = uri

    def get(self):
        print "RestResource GET:", self.uri
        return self._sendRequest('GET')

    def post(self, **kwargs):
        postData = urllib.urlencode(kwargs)
        mimeType = 'application/x-www-form-urlencoded'
        return self._sendRequest('POST', postData, mimeType)

    def put(self, data, mimeType):
        return self._sendRequest('POST', data, mimeType)

    def delete(self):
        return self._sendRequest('DELETE')

    def _sendRequest(self, method, data="", mimeType=None):
        headers = {}
        if mimeType:
            headers['Content-Type'] = mimeType
        if data:
            headers['Content-Length'] = str(len(data))
        return client.getPage(self.uri, method=method, postdata=data, headers=headers)
