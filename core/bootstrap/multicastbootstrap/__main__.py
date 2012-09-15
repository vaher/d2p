#!/usr/bin/env python3


import sys,os.path
_ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(_ROOTDIR)

sys.path.append(os.path.join(_ROOTDIR,  '..', '..', 'libs', 'tornado', 'build', 'lib'))
import multicastbootstrap
sys.path.remove(_ROOTDIR)

if __name__ == '__main__':
    multicastbootstrap.main()
