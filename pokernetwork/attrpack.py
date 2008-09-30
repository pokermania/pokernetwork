# Copyright (C)             2008 Bradley M. Kuhn <bkuhn@ebb.org>
#
# This program gives you software freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version of the AGPL.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#  Bradley M. Kuhn <bkuhn@ebb.org>

# methods for looking up stats, and allowing for mix-in of different types
# of stats.  Each stat is usually looked up with a UserStatsAccessor class
# (or a subclass thereof).  The UserStatsLookup class itself (or
# subclasses thereof) are the things used by other classes to lookup
# statistics.

# I decided to make the elements for lookup a table, a user_serial, and a
# service.  I felt this was the most likely set of objects that would be
# used for looking up stats, and of course they need not be used if not
# needed.

############################################################################
class AttrsFactory:

    """The Attrs system is designed to be a flexible and arbitrary key/value
    system for object types when we want poker-network to have
    easily-implemented aribitrary data associated with a particular item.

    The public interface usage looks something like this (although "Attr" will
    be replaced with "SOMETHING" since this is a virtual base class):

        attrLookup = AttrFactory().getClass("MySpecialStuff")(args...)

        answerGetSupported = attrLookup.supportedAttrsAsPacket(args...)
        #  Send packet inside answerGetSupported to client...
        answerGetAttrs     = attrLookup.allStatsAsPacket(args...)
        #  Send packet inside answerGetAttrs to client...

    The general idea is that only poker-network code that knows a *thing*
    about what key/value attributes are being supported for the particular
    SOMETHING are specific to the classes defined by "MySpecialStuff".

    The Attr base classes are currently used to implement the UserStats (in
    userstats.py) and TourneyAttrs (in tourneyattrs.py).  You may want to read
    the code in those files before reading further here, because understanding
    the code here in detail is only needed if you want to write a new
    SOMETHING.

         Actually Using This Class To Implement New Attribute System
        -----------------------------------------------------------

    If you want to implement an attribute system for SOMETHING, you should
    (initially) derive from three classes, AttrFactory (this one),
    AttrLookup, and AttrAccessor.  For this one:
         SOMETHINGFactory (base class: AttrFactory)
             what to override:
                 __init__() : set the right module name of where are in.

    Note that you'll have to implement new packet types to use this.  See
    the doc string on class AttrLookup for details.
"""
    def __init__(self, moduleStr = 'attrpack', classPrefix = "Attrs", defaultClass = "AttrsLookup"):
        self.moduleStr = moduleStr
        self.classPrefix = classPrefix
        self.defaultClass = defaultClass
    # ----------------------------------------------------------------------
    def error(self, string):
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        print string
    # ----------------------------------------------------------------------
    def getClass(self, classname):
        classname = self.classPrefix + classname + "Lookup"
        try:
            return getattr(__import__(self.moduleStr, globals(), locals(), [classname]), classname)
        except AttributeError, ae:
            self.error(ae.__str__())
        classname = self.defaultClass
        return getattr(__import__(self.moduleStr, globals(), locals(), [classname]), classname)
############################################################################
class AttrsAccessor:

    """AttrsAccessor is a base class for doing the key/value lookups for
    the attribute system.  Typically, you will want to override:
         __init__()/getSupportedList():
              to set the attrsSupported and expected LookupArgs instance variables.
         _lookupValidAttr()
              you may want to set it up with the proper arguments expected.
    """
    def __init__(self):
        self.attrsSupported = []
        self.expectLookupArgs = []
    # ----------------------------------------------------------------------
    def getSupportedAttrsList(self):
        """returns list of attributes supported for lookup by this class"""
        return self.attrsSupported
    # ----------------------------------------------------------------------
    def getAttrValue(self, attr, *args, **kwargs):
        """returns the value associated with the attribute, attr.
            Arguments:
                self:    this Accessor class object
                attr:    the key to look up.
            Remaining arguments are passed directly to self._lookupValidStat()
        """
        if not attr in self.attrsSupported:
            self.error("invalid attribute, %s" % attr)
            return None

        if len(args) > 0:
            self.error("keyword arguments only are supported for getAttrValue.  Ignoring these args: %s" % args.__str__())
        extraList = filter(lambda g: not g in self.expectLookupArgs, kwargs.keys())
        missingList = filter(lambda g: not g in kwargs.keys(), self.expectLookupArgs)
        if len(missingList) > 0:
            self.error("The following required argument(s) missing for getAttrValue, lookup will surely fail: %s" 
                       % missingList.__str__())
        if len(extraList) > 0:
            self.error("Ignoring these extraneous arguments for getAttrValue: %s" 
                       % extraList.__str__())
        return self._lookupValidAttr(attr, **kwargs)
    # ----------------------------------------------------------------------
    def _lookupValidAttr(self, attr, **kwargs):
        """This is an abstract method; it should be overridden by your class.
        Arguments:
            self:    this Accessor class object
            attr:    the key to look up.
        Remaining arguments are specific to your subclass.  You should
        make all of them kwargs.
        """
        raise NotImplementedError("_lookupValidAttr NOT IMPLEMENTED IN ABSTRACT BASE CLASS")
    # ----------------------------------------------------------------------
    def error(self, string):
        """Handle an error message.  Ultimately calls self.message().

        Keyword arguments:
                string: error message to send.
        """
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        """Note a message about an action.  Currently just does "print"

        Keyword arguments:
            string: message to print.
        """
        print string
############################################################################
class AttrsLookup:

    """AttrsLookup is a base class for aggregating a bunch of
    AttrsAccessor classes into a single lookup class.  the attribute
    system.  Typically, you should not need to override any methods here,
    because you will mostly be overriding them in the
    """

    def __init__(self, attr2accessor = {},  packetClassesName = "Attrs", requiredAttrPacketFields = []):
        """Initialize the attribute lookup class.  This should be called
        by your base class.

        Keyword arguments:
            attr2accessor: A dict ({} by default) with keys that are
                           strings, the attributes to be looked up, and
                           values that are subclasses of AttrsAccessor
                           that provide those values.

            requiredAttrPacketFields: This is a list of strings ([] by
                                      default) that are required fields in
                                      the PacketPokerSOMETHING packet and
                                      should not be thrown into the
                                      attrsDict, but should be present as
                                      keyword arguments to a
                                      getAttrsAsPacket() method call.

            packetClassesName: The string that is used in the name of the
                               packet classes that correspond to your
                               subclass. (replacing SOMETHING below):

        Note that for this class to work properly, you will also need to
        implement the following packet types in pokerpackets.py:
            PacketPokerGetSOMETHING           (base class: PacketPokerGetAttrs)
            PacketPokerSOMETHING              (base class: PacketPokerAttrs)
            PacketPokerGetSupportedSOMETHING  (base class: PacketPokerGetSupportedAttrs)
            PacketPokerSupportedSOMETHING     (base class: PacketPokerSupportedAttrs)
        """
        self.attr2accessor = attr2accessor
        self.packetAbbrev2packetClass = {}
        self.requiredPacketFields = requiredAttrPacketFields
        self.packetDescription = packetClassesName

        # Get the appropriate PacketPoker classes that correspond to the
        # four operations we support and the type

        for (pp, val) in [ ('send', ''), ('supported', 'Supported') ]:
            self.packetAbbrev2packetClass[pp] = self._getPacketClass(val, packetClassesName)
    # ----------------------------------------------------------------------
    def _getPacketClass(self, prefix, classname):
        """Internal, private method.  Used by __init__ to lookup the
        corresponding packets."""

        classname = "PacketPoker" + prefix + classname
        try:
            return getattr(__import__('pokerpackets', globals(), locals(), [classname]), classname)
        except AttributeError, ae:
            self.error(ae.__str__())
        classname = "PacketPoker" + prefix + "Attrs"
        return getattr(__import__('pokerpackets', globals(), locals(), [classname]), classname)
    # ----------------------------------------------------------------------
    def getAttrValue(self, attr, *args, **kwargs):
        """Returns the attribute value, using the appropriate accessor
        class, for attr.
            Arguments:
                self: this Lookup object.
                attr: the attribute key to be looked up.
            Remaining arguments are passed to the Accessor class.
        """
        if self.attr2accessor.has_key(attr):
            return self.attr2accessor[attr].getAttrValue(attr, *args, **kwargs)
        else:
            self.error("unsupported attribute, %s, for %s" % (attr, self.packetDescription))
            return None
    # ----------------------------------------------------------------------
    def getAttrsAsPacket(self, **kwargs):
        """Returns the PacketPokerAttrs-derived packet with the key/value
        correctly placed.  Fields that must be pulled out and should not
        appear in the attrsDict of the packet should be handled by the pull"""
        packetClass = self.packetAbbrev2packetClass['get']
        attrs2vals = {}
        packetKwargs = {}

        # Next, loop through kwargs, building another one for the packetClass,
        # and verifying that all the requiredPacketFields are present.

        for fieldName in self.requiredPacketFields:
            if not kwargs.has_key(fieldName):
                msg = "PacketPoker%s requires field %s; getAttrsAsPacket called without it" % (self.packetDescription, fieldName)
                self.error(msg)
                return PacketPokerError(message = "SERVER ERROR: " +  msg,
                                        other_type = packetClass.type)
            packetKwargs[fieldName] = kwargs[fieldName]
            
        for attr in self.attr2accessor.keys():
            # Note below that getAttrValue may get more kwargs than
            # expected, since we're sending along the ones for the packets
            # as well.  This is probably no harm done, since
            # getAttrValue() is only going to scream if it is missing one
            # it expects, not if it has extras
            attrs2vals[attr] = self.getAttrValue(attr, **kwargs)

        # Next, add results from the loop to the attrsDict, which the
        # packetClass should be expecting.
        packetKwargs['attrsDict'] = attrs2vals

        return packetClass(**packetKwargs)
    # ----------------------------------------------------------------------
    def getSupportedAttrsAsPacket(self):
        """Returns the PacketPokerAttrsSupported-derived packet with a
        list of attributes that are supported by this class."""

        return self.packetAbbrev2packetClass['getSupported'](attrs = self.attr2accessor.keys())
    # ----------------------------------------------------------------------
    def error(self, string):
        """Handle an error message.  Ultimately calls self.message().

        Keyword arguments:
                string: error message to send.
        """
        self.message("ERROR " + string)
    # ----------------------------------------------------------------------
    def message(self, string):
        """Note a message about an action.  Currently just does "print"

        Keyword arguments:
            string: message to print.
        """
        print string
############################################################################
