#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

import sqlite3
import syncpc

factory = syncpc.ClientFactory('clientdb')

def gotProtocol(p):
  factory.sync(p)

if __name__=='__main__':
  point = TCP4ClientEndpoint(reactor, 'localhost', 12345)
  d = point.connect(factory)
  d.addCallback(gotProtocol)
  reactor.run()


