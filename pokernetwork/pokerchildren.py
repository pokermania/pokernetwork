#
# Copyright (C) 2004, 2005, 2006 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
import sys
import os
import platform
if platform.system() == "Windows" :
    import win32api, win32pdhutil, win32con, win32process
    from underware import python_mywin32
    from win32com.shell import shell, shellcon

import sys
import socket
from os.path import expanduser, exists, abspath
from os import environ
from string import split, join, replace
from time import sleep
from shutil import copy

import libxml2

from twisted.python.failure import Failure
from twisted.internet import reactor

from pokernetwork import dispatch

def killProcName(procname_ori):
    print "killing " + procname_ori
    python_mywin32.killProcessByName(procname_ori)
    return
    procname=procname_ori.replace(".exe","")

    # Change suggested by Dan Knierim, who found that this performed a
    # "refresh", allowing us to kill processes created since this was run
    # for the first time.
    try:
        win32pdhutil.GetPerformanceAttributes('Process','ID Process',procname)
    except:
        pass

    pids = win32pdhutil.FindPerformanceAttributesByName(procname)
    try:
        pids.remove(win32api.GetCurrentProcessId())
    except ValueError:
        pass

    if len(pids)==0:
        result = "Can't find %s" % procname
    elif len(pids)>1:
        result = "Found too many %s's - pids=`%s`" % (procname,pids)
    else:
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0,pids[0])
        win32api.TerminateProcess(handle,0)
        win32api.CloseHandle(handle)
        result = ""

    return result

class PokerChild(dispatch.EventDispatcher):
    def __init__(self, config, settings):
        dispatch.EventDispatcher.__init__(self)
        self.config = config
        self.settings = settings
        self.verbose = settings.headerGetInt("/settings/@verbose")
        self.pid = None
        self.commandLine = None
        self.commandName = None
        self.pidFile = None
        self.spawnInDir = None
        self.ready = False

        if platform.system() == "Windows":
            IDLList = shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_APPDATA)
            localData = shell.SHGetPathFromIDList(IDLList) + "\Pok3d"
            self.pokerrc = localData
        else:
            if settings.headerGet("/settings/user/@path"):
                self.pokerrc = expanduser(settings.headerGet("/settings/user/@path"))
            else:
                self.pokerrc = '.'

    def kill(self):
        if not self.ready:
            return -1

        path = self.pokerrc + "/" + self.pidFile + ".pid"
        if not self.pid:
            if exists(path):
                fd = file(path, "r")
                self.pid = int(fd.read(512))
                fd.close()
                if self.verbose:
                    print "found %s pid %d in %s" % ( self.commandName, self.pid, path )
        else:
            if self.verbose:
                print "killing " + " ".join(self.commandLine)

        if self.pid:
            if platform.system() == "Windows":
                try:
                    tokill=self.commandName
                    killProcName(tokill)
                except:
                    print "%s terminate()" % ( tokill )
            else:
                try:
                    os.kill(self.pid, 9)
            	    try:
                        os.waitpid(self.pid, 0)
                    except OSError:
                        print "cannot wait for %s process %d to die : %s" % ( self.commandName, self.pid, sys.exc_value )

                except:
                    print "%s kill(%d,9) : %s" % ( self.commandName, self.pid, sys.exc_value )

        if exists(path):
            os.remove(path)

        pid = self.pid
        self.pid = None
        return pid

    def savepid(self, what, pid):
        path = self.pokerrc + "/" + what + ".pid"
        fd = file(path, "w")
        fd.write(str(pid))
        fd.close()
        if self.verbose:
            print "%s pid %d saved in %s" % ( what, pid, path )
        return pid
    
    def spawn(self):
        if not self.ready:
            return False
        
        print "%s: %s" % (self.commandName, join(self.commandLine))
        import signal
        handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if self.spawnInDir:
            self.commandLine[0] = abspath(self.commandLine[0])
            cwd = os.getcwd()
            if self.verbose:
                print "spawn in " + self.spawnInDir
            os.chdir(self.spawnInDir)
        if platform.system() == "Windows":
            commandLine = map(lambda x: "'%s'" % x, self.commandLine)
        else:
            commandLine = self.commandLine
        pid = os.spawnv(os.P_NOWAIT, self.commandLine[0], commandLine)
        if self.spawnInDir:
            os.chdir(cwd)
        signal.signal(signal.SIGINT, handler)
        self.pid = self.savepid(self.pidFile, pid)
        return True

class PokerChildren:

    def __init__(self, config, settings):
        self.config = config
        self.settings = settings
        self.verbose = settings.headerGetInt("/settings/@verbose")
        self.children = []

    def spawn(self, child):
        if child.spawn():
            self.children.append(child)
            return True
        else:
            return False
        
    def kill(self, child):
        child.kill()
        self.children.remove(child)
        
    def killall(self):
        status = True
        for child in self.children:
            status = child.kill() and status
        return status

class PokerChildBrowser(PokerChild):
    def __init__(self, config, settings, path):
        PokerChild.__init__(self, config, settings)
        self.verbose = settings.headerGetInt("/settings/@verbose")
        self.browser = settings.headerGet("/settings/web/@browser") or "/usr/bin/firefox"
        if "http://" in path:
            self.url = path
            path = ""
        else:
            self.url = settings.headerGet("/settings/web")
        self.ready = self.configure(path)
        if self.ready:
            self.spawn()
        else:
            print "PokerChildBrowser: no URL in /settings/web, cannot browse web"

    def configure(self, path):
        if not self.url:
            return False

        self.commandLine = [ self.browser, self.url + path ]
        self.commandName = split(self.commandLine[0],"/").pop()
        self.pidFile = self.commandName
        if self.verbose:
            print "PokerChildBrowser: command line " + str(self.commandLine)
        return True

    def spawn(self):
        if platform.system() == "Windows":
			try:
				win32api.ShellExecute(0, None, self.commandLine[1], None, None, 1)
			except:
				target = win32api.RegQueryValue(win32con.HKEY_CLASSES_ROOT, "HTTP\shell\open\command")
				raise Exception("*CRITICAL*: failed to start browser at: %s" % target)
			return True
        else:
            return PokerChild.spawn(self)


from twisted.internet.protocol import ProcessProtocol
from twisted.internet import error

RSYNC_DONE = "//event/pokernetwork/pokerchildren/rsync_done"
RSYNC_FAILED = "//event/pokernetwork/pokerchildren/rsync_failed"
RSYNC_NO_NETWORK = "//event/pokernetwork/pokerchildren/rsync_no_network"
RSYNC_HOST_DOES_NOT_RESPOND = "//event/pokernetwork/pokerchildren/rsync_host_does_not_respond"

class PokerRsync(PokerChild, ProcessProtocol):

    def __init__(self, config, settings, rsync):
        PokerChild.__init__(self, config, settings)
        self.verbose = settings.headerGetInt("/settings/@verbose")
        self.ready = self.configure(rsync)
        self.chunks = []
        self.errors = []

    def configure(self, rsync):
        settings = self.settings
        source = settings.headerGet("/settings/rsync/@source")
        proxy = settings.headerGet("/settings/rsync/@proxy")

        if platform.system() == "Windows":
            try:
                reg_key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, "Software\Mekensleep\Pok3d")
            except:
                reg_key = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE, "Software\Mekensleep\Pok3d")

            target = win32api.RegQueryValue(reg_key, "")
            win32api.RegCloseKey(reg_key)
        else:
            target = settings.headerGet("/settings/rsync/@target")

        if proxy:
            environ['RSYNC_PROXY'] = proxy
        
        self.rsync = [ settings.headerGet("/settings/rsync/@path") ] + map(lambda x:
                                                                           reduce(lambda a, b: replace(a, b[0], b[1]), [x,
                                                                                                                        ( "@SOURCE@", source ),
                                                                                                                        ( "@TARGET@", target )]
                                                                                  ),
                                                                           rsync)
        if platform.system() == "Windows":
            self.rsync = map(lambda x: '"' + x + '"', self.rsync)
            import re
            self.rsync = map(lambda x: re.sub(r'(.):\\(.*)', r'/cygdrive/\1/\2', x), self.rsync)
        return True

    def spawn(self):
        if self.verbose > 1:
            print "PokerRsync::spawn: " + join(self.rsync)
        dir = self.settings.headerGet("/settings/rsync/@dir")
        if platform.system() == "Windows":
            self.proc = reactor.spawnProcess(self, self.rsync[0], args = self.rsync[1:], path = dir, win32flags = win32process.DETACHED_PROCESS)
        else:
            childFDs = { 1: 'r', 2: 'r' }
            self.proc = reactor.spawnProcess(self, self.rsync[0], args = self.rsync[1:], path = dir,
                                             childFDs = childFDs)

    def line(self, string):
        print "%s" % string

    def errReceived(self, chunk):
        print "ERROR: PokerRsync " + chunk
        self.errors.append(chunk)
        
    def outReceived(self, chunk):
        self.chunks.append(chunk)
        if "\n" in chunk:
            lines = join(self.chunks).split("\n")
            self.chunks = []
            last = lines.pop()
            if last != '':
                self.chunks.append(last)
            for line in lines:
                self.line(line)

    def done(self):
        self.publishEvent(RSYNC_DONE)
        
    def failed(self, logs, reason):
        host_does_not_respond = "failed to connect to"
        if logs.find(host_does_not_respond) != -1:
            self.publishEvent(RSYNC_HOST_DOES_NOT_RESPOND, logs,reason)

        errror_no_network = ("getaddrinfo", "Temporary failure in name resolution")
        if logs.find(errror_no_network[0]) != -1 and logs.find(errror_no_network[1]):
            self.publishEvent(RSYNC_NO_NETWORK, logs,reason)

        self.publishEvent(RSYNC_FAILED, logs,reason)
        
    def outConnectionLost(self):
        pass

    def processEnded(self, reason):
        if isinstance(reason.value, error.ProcessDone):
            self.done()
        else:
            if self.verbose > 2: print "PokerRsync::processEnded: " + str(reason)
            self.failed("".join(self.errors), reason)
