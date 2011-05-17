#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet import reactor

import syncps

def main():
  reactor.listenTCP(12345, syncps.ServerFactory('serverdb'))
  reactor.run()

if __name__ == '__main__':
  main()
