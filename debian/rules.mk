# -*- makefile -*-
#
# Copyright (C) 2005 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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
# 
include /usr/share/cdbs/1/rules/debhelper.mk
# prevent inclusion of makefile.mk because its rules do not fit our purpose
_cdbs_class_makefile := 1
include /usr/share/cdbs/1/class/autotools-vars.mk
include /usr/share/cdbs/1/class/makefile-vars.mk

ifneq (ccache,$(findstring ccache,$(DEB_BUILD_OPTIONS)))
        DEB_CONFIGURE_EXTRA_FLAGS += --without-ccache
endif

is_debug_package=$(if $(findstring noopt,$(DEB_BUILD_OPTIONS)),yes,)

DEB_MAKE_INSTALL_TARGET = install DESTDIR=$(DEB_DESTDIR)

python_version=`expr '$@' : '.*python\([0-9].[0-9]\)'`

DEB_CONFIGURE_SCRIPT_ENV = CC="$(CC)" CXX="$(CXX)" CFLAGS="$(CFLAGS)" CXXFLAGS="$(CXXFLAGS)" PYTHON_VERSION_CONSTRAINT="=$(python_version)" 
DEB_CONFIGURE_NORMAL_ARGS += --srcdir=..

DEB_PYTHON_VERSIONS = 2.3 2.4
DEB_PYTHON_PACKAGES := $(strip $(filter $(patsubst %,python%%,$(DEB_PYTHON_VERSIONS)),$(DEB_ALL_PACKAGES)))

DEB_DH_MAKESHLIBS_ARGS = -n

common-configure-arch common-configure-indep:: $(patsubst %,config-status/%,$(DEB_PYTHON_PACKAGES)) 
$(patsubst %,config-status/%,$(DEB_PACKAGES)):: $(DEB_SRCDIR)/configure
	if [ ! -f $(if $(DEB_BUILDDIR_$(cdbs_curpkg)),$(DEB_BUILDDIR_$(cdbs_curpkg)),$(DEB_BUILDDIR))/config.status ] ; then \
		$(DEB_CONFIGURE_INVOKE) $(cdbs_configure_flags) $(DEB_CONFIGURE_EXTRA_FLAGS) $(DEB_CONFIGURE_USER_FLAGS) ; \
	fi
	mkdir -p config-status && touch config-status/$(cdbs_curpkg)

$(DEB_SRCDIR)/config.status:: $(DEB_SRCDIR)/configure
	./configure --enable-maintainer-mode

$(DEB_SRCDIR)/configure:: $(DEB_SRCDIR)/bootstrap $(DEB_SRCDIR)/configure.ac
	sh bootstrap
	chmod a+x $@

DEB_PYTHON_FILES = $(patsubst debian/python-%,%,$(shell ls debian/python-*{dirs,docs,postinst,install,templates,config,init} 2>/dev/null || echo))
DEB_PYTHON_PACKAGE_FILES = $(foreach file,$(DEB_PYTHON_FILES),$(foreach version,$(DEB_PYTHON_VERSIONS),debian/python$(version)-$(file)))

$(DEB_SRCDIR)/configure:: $(DEB_PYTHON_PACKAGE_FILES)

$(DEB_PYTHON_PACKAGE_FILES):: $(patsubst %,debian/python-%,$(DEB_PYTHON_FILES))
	python_file=debian/python-`expr $@ : 'debian/python...-\(.*\)'` ; \
	sed -e 's/@PYTHON_VERSION@/'$(python_version)'/g' < $$python_file > $@ 

clean:: $(DEB_SRCDIR)/config.status
	for python_file in $(DEB_PYTHON_FILES) ; do \
		if [ -f debian/python-$$python_file ] ; then \
			rm -f debian/python?.?-*$$python_file ; \
		fi ; \
	done
	rm -fr config-status
	$(MAKE) maintainer-clean

$(patsubst %,cleanbuilddir/%,$(DEB_PACKAGES))::
	-if test -n "$(DEB_BUILDDIR_$(cdbs_curpkg))" && test "$(DEB_BUILDDIR_$(cdbs_curpkg))" != "$(DEB_SRCDIR)"; then rm -fr "$(DEB_BUILDDIR_$(cdbs_curpkg))"; fi

DEB_MAKE_INVOKE = $(DEB_MAKE_ENVVARS) make -C $(if $(DEB_BUILDDIR_$(cdbs_curpkg)),$(DEB_BUILDDIR_$(cdbs_curpkg)),$(DEB_BUILDDIR)) CFLAGS=$(if $(CFLAGS_$(cdbs_curpkg)),"$(CFLAGS_$(cdbs_curpkg))","$(CFLAGS)") CXXFLAGS=$(if $(CXXFLAGS_$(cdbs_curpkg)),"$(CXXFLAGS_$(cdbs_curpkg))","$(CXXFLAGS)") 

$(patsubst %,build/%,$(DEB_PACKAGES)) :: 
	$(DEB_MAKE_INVOKE) $(DEB_MAKE_BUILD_TARGET)

DEB_MAKE_INSTALL_TARGET = install DESTDIR=$(DEB_DESTDIR)

common-install-arch common-install-indep:: $(patsubst %,install/%,$(DEB_PACKAGES))
$(patsubst %,install/%,$(DEB_PACKAGES)) :: 
	$(DEB_MAKE_ENVVARS) make -C $(if $(DEB_BUILDDIR_$(cdbs_curpkg)),$(DEB_BUILDDIR_$(cdbs_curpkg)),$(DEB_BUILDDIR)) $(DEB_MAKE_INSTALL_TARGET)

$(patsubst %,binary-install/%,$(DEB_PYTHON_PACKAGES)) :: binary-install/%:
	dh_python -p$(cdbs_curpkg) -V $(python_version)

