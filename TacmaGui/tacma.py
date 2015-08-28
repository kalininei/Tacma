#!/usr/bin/env python

import sys
from PyQt5 import QtWidgets
import tacmaopt
import mainwinwid


def main():
    try:
        # config.py will be copied to actual directory
        # only during installation procedure.
        # If there is no such module -> we are in the debug session
        import config
        import os.path
        tacmaopt.ProgOptions.wdir = config.working_directory
        tacmaopt.ProgOptions.ver = config.version
        if not os.path.exists(tacmaopt.ProgOptions.wdir):
            os.makedirs(tacmaopt.ProgOptions.wdir)
    except:
        tacmaopt.ProgOptions.wdir = '.'
        tacmaopt.ProgOptions.ver = 'Debug'

    # -- read options
    tacmaopt.opt.read()

    # -- initialize qt application
    app = QtWidgets.QApplication(sys.argv)

    mw = mainwinwid.MainWindow(tacmaopt.opt.wfile)
    mw.show()

    # start gui loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
