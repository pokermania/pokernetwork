# Copyright 1999-2005 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header$

inherit eutils

DESCRIPTION="poker-network is a python library that implements a poker game (server and client)"
HOMEPAGE="http://gna.org/projects/pokersource"
MY_P="${PN}-${PV}.tar.gz"
SRC_URI="http://download.gna.org/pokersource/sources/${MY_P}"
SLOT="0"
LICENSE="GPL-2.1"
KEYWORDS="x86 amd64"
IUSE=""

DEPEND=">=sys-devel/automake-1.9.0 
      dev-util/pkgconfig 
      >=dev-lang/python-2.4.0 
      dev-python/soappy 
      dev-python/mysql-python 
      dev-python/pygtk 
      dev-python/twisted 
      dev-util/glade 
      dev-libs/glib 
      >=dev-games/poker-engine-1.0.22
      dev-games/pypoker-eval 
      net-misc/rsync"

src_unpack() {
	unpack ${MY_P}
	if ls ${FILESDIR}/${PVR}*.patch 2>/dev/null
		then
		for i in ${FILESDIR}/${PVR}*.patch
		  do
		  epatch $i
		done
	fi
}


src_install () {
	make install DESTDIR=${D} || die "einstall failed"
}
