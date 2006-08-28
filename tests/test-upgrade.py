
import os
import sys

sys.path.insert(0, "../")
sys.path.insert(0, "../../poker-engine/pokerengine")
sys.path.insert(0, "U:/new_pok3d/underware/envwin32/python/Lib/site-packages")
sys.path.insert(0, "U:/new_pok3d/underware/envwin32/python/Lib/site-packages/win32")
sys.path.insert(0, "U:/new_pok3d/underware/envwin32/python/Lib/site-packages/win32/lib")

sys.path.insert(0, "U:/new_pok3d/underware/underware/python/")

os.environ["path"] += ";U:/new_pok3d/underware/envwin32/python/Lib/site-packages/win32"
os.environ["path"] += ";U:/new_pok3d/underware/envwin32/python/Lib/site-packages/pywin32_system32"

#if os.name != "posix":
#    from twisted.internet import win32eventreactor
#    win32eventreactor.install()

from pokernetwork import upgrade
from pokerengine import pokerengineconfig

import unittest

from twisted.python.failure import Failure
from twisted.internet import reactor

class UpgradeTestCase(unittest.TestCase):

    def setUp(self):
        self.config = pokerengineconfig.Config( ["U:/new_pok3d/underware/envwin32"] )
        self.settings = pokerengineconfig.Config( ["U:/new_pok3d/underware/envwin32"] )
        self.config.load("poker.client.xml")
        self.settings.load("poker.client.xml")
        self.settings.headerSet("/settings/rsync/@path", "U:/new_pok3d/underware/envwin32/bin-cygwin/rsync.exe")
        self.settings.headerSet("/settings/rsync/@dir", "U:/new_pok3d/underware/envwin32/bin-cygwin")
        self.upgrade = upgrade.Upgrader(self.config, self.settings)

    def tearDown(self):
        self.upgrade = None

    def testIsNewVersionAvailable(self):
        self.upgrade.checkClientVersion( (1, 0, 5) )

def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UpgradeTestCase))
    return suite
    
def Run(verbose = 2):
    unittest.TextTestRunner(verbosity=verbose).run(GetTestSuite())
    
if __name__ == '__main__':
    Run()
    print "TOTO"

