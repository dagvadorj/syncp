#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

import os
import logging
import sqlite3
import stat
import time

# Configure logger
logger = logging.getLogger('syncp logger')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
  '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def listFiles(path):
  """
  Outputs the list of files 
  """
  outputList = []
  for root, dirs, files in os.walk(path):
    for f in files:
      outputList.append('/'.join([root, f]))
  return outputList
 
class Client(LineReceiver):

  delimiter = '\n'
  
  token = ''
  length = 0
  temp = ''
  path = ''
  
  def rawDataReceived(self, data):
    data, rest = data[:self.length], data[self.length:]
    self.length -= len(data)
    self.temp += data    
    if self.length == 0:
      dir = '/'.join(self.path.split('/')[:-1])
      if not os.path.exists(dir):
        os.makedirs(dir)
      incoming = open(self.path, 'w')
      incoming.write(self.temp)
      incoming.close()
      self.setLineMode(rest)
      
  def lineReceived(self, data):
    logger.info(data)
    parts = data.split()
    verb = str(parts[0])
    self.token = str(parts[1])
    path, sync, mtime, index = self.factory.getIndex(self.token)
    if verb == 'PUT':
      self.length = int(parts[2])
      self.path = path + '/' + ' '.join(parts[3:])
      self.temp = ''
      self.setRawMode()
    elif verb == 'DELETE':
      try: os.remove(path + '/' + ' '.join(parts[2:]))
      except: pass
    elif verb == 'UPDATE':
      self.factory.updateIndex(self.token, int(parts[2]))
      time.sleep(10)
      self.factory.sync(self)
    elif verb == 'FINE':
      files = listFiles(path)
      deleting = index
      for f in files:
        try: deleting.remove(f)
        except: pass
        ctime = os.stat(f)[stat.ST_CTIME]
        if ctime > mtime:
          temp = open(f, 'r')
          r = temp.read()
          self.transport.write('PUT ' + str(self.token) + 
            ' ' + str(len(r)) + ' ' + str(f[len(path)+1:]) + '\n')
          self.transport.write(r)
          temp.close()
      for f in deleting:
        self.transport.write('DELETE ' + str(self.token) + 
          ' ' + str(f[len(path)+1:]) + '\n')
      
      self.transport.write('UPDATE ' + str(self.token) + '\n')

class ClientFactory(Factory):  
  protocol = Client
  
  def __init__(self, db):
    self.db = db
  
  def getIndex(self, token):
    conn = sqlite3.connect(self.db)
    c = conn.cursor()
    c.execute('select path, sync, mtime from users where token=?', 
      (token, ))
    path, sync, mtime = c.fetchone()
    c.execute('select file from indices where token=?',
      (token, ))
    files = c.fetchall()
    conn.close()
    index = []
    for f in files: index.append(f[0])
    return path, sync, mtime, index
    
  def updateIndex(self, token, sync):
    conn = sqlite3.connect(self.db)
    c = conn.cursor()
    c.execute('select path from users where token=?', 
      (token, ))
    path = c.fetchone()[0]
    mtime = os.stat(path)[stat.ST_MTIME]
    files = listFiles(path)
    c.execute('delete from indices where token=?', (token, ))
    for f in files:
      c.execute('insert into indices (file, token) values (?,?)', 
        (f, token))
    conn.commit()
    c.execute('update users set sync=?, mtime=? where token=?',
      (sync, mtime, token))
    conn.commit()
    conn.close()
  
  def sync(self, p):
    conn = sqlite3.connect(self.db)
    c = conn.cursor()
    c.execute('select token, path, sync from users')  
    users = c.fetchall()
    for user in users:
      token, path, sync = user
      p.transport.write('SYNC ' + str(token) + ' ' + str(sync) + '\n')
    conn.close()

