#!/bin/sh
#
# Generic package build script
#
# $Id$
#
# Package maintainers: if the original source is not distributed as a
# (possibly compressed) tarball, set the value of ${src_orig_pkg_name},
# and redefine the unpack() helper function appropriately.
# Also, if the Makefile rule to run the test suite is not "check", change
# the definition of ${test_rule} below.

# find out where the build script is located
tdir=`echo "$0" | sed 's%[\\/][^\\/][^\\/]*$%%'`
test "x$tdir" = "x$0" && tdir=.
scriptdir=`cd $tdir; pwd`
# find src directory.
# If scriptdir ends in SPECS, then topdir is $scriptdir/..
# If scriptdir ends in CYGWIN-PATCHES, then topdir is $scriptdir/../..
# Otherwise, we assume that topdir = scriptdir
topdir1=`echo ${scriptdir} | sed 's%/SPECS$%%'`
topdir2=`echo ${scriptdir} | sed 's%/CYGWIN-PATCHES$%%'`
if [ "x$topdir1" != "x$scriptdir" ] ; then # SPECS
  topdir=`cd ${scriptdir}/..; pwd`
else
  if [ "x$topdir2" != "x$scriptdir" ] ; then # CYGWIN-PATCHES
    topdir=`cd ${scriptdir}/../..; pwd`
  else
    topdir=`cd ${scriptdir}; pwd`
  fi
fi

tscriptname=`basename $0 .sh`
export PKG=`echo $tscriptname | sed -e 's/\-[^\-]*\-[^\-]*$//'`
export VER=`echo $tscriptname | sed -e "s/${PKG}\-//" -e 's/\-[^\-]*$//'`
export REL=`echo $tscriptname | sed -e "s/${PKG}\-${VER}\-//"`
# BASEPKG refers to the upstream base package
# SHORTPKG refers to the Cygwin package
# Normally, these are identical, but if the Cygwin package name is different
# from the upstream package name, you will want to redefine BASEPKG.
# Example: For Apache 2, BASEPKG=httpd-2.x.xx but SHORTPKG=apache2-2.x.xx
export BASEPKG=${PKG}-${VER}
export SHORTPKG=${PKG}-${VER}
export FULLPKG=${SHORTPKG}-${REL}

# determine correct decompression option and tarball filename
export src_orig_pkg_name=
if [ -e "${src_orig_pkg_name}" ] ; then
  export opt_decomp=? # Make sure tar punts if unpack() is not redefined
elif [ -e ${BASEPKG}.tar.bz2 ] ; then
  export opt_decomp=j
  export src_orig_pkg_name=${BASEPKG}.tar.bz2
elif [ -e ${BASEPKG}.tar.gz ] ; then
  export opt_decomp=z
  export src_orig_pkg_name=${BASEPKG}.tar.gz
elif [ -e ${BASEPKG}.tgz ] ; then
  export opt_decomp=z
  export src_orig_pkg_name=${BASEPKG}.tgz
elif [ -e ${BASEPKG}.tar ] ; then
  export opt_decomp=
  export src_orig_pkg_name=${BASEPKG}.tar
else
  echo "Cannot find PKG:${SHORTPKG} VER:${VER} REL:${REL}.  Rename $0 to"
  echo "something more appropriate, and try again."
  exit 1
fi

export src_orig_pkg=${topdir}/${src_orig_pkg_name}

# determine correct names for generated files
export src_pkg_name=${FULLPKG}-src.tar.bz2
export src_patch_name=${FULLPKG}.patch
export bin_pkg_name=${FULLPKG}.tar.bz2

export src_pkg=${topdir}/${src_pkg_name}
export src_patch=${topdir}/${src_patch_name}
export bin_pkg=${topdir}/${bin_pkg_name}
export srcdir=${topdir}/${BASEPKG}
export objdir=${srcdir}/.build
export instdir=${srcdir}/.inst
export srcinstdir=${srcdir}/.sinst
export checkfile=${topdir}/${FULLPKG}.check

prefix=/usr
sysconfdir=/etc
localstatedir=/var
if [ -z "$MY_CFLAGS" ]; then
  MY_CFLAGS="-O2"
fi
if [ -z "$MY_LDFLAGS" ]; then
  MY_LDFLAGS=
fi

export install_docs="\
	ABOUT-NLS \
	ANNOUNCE \
	AUTHORS \
	BUG-REPORTS \
	CHANGES \
	CONTRIBUTORS \
	COPYING \
	COPYRIGHT \
	CREDITS \
	CHANGELOG \
	ChangeLog* \
	FAQ \
	HOW-TO-CONTRIBUTE \
	INSTALL \
	KNOWNBUG \
	LEGAL \
	LICENSE \
	NEWS \
	NOTES \
	PROGLIST \
	README \
	RELEASE_NOTES \
	THANKS \
	TODO \
	USAGE \
"
export install_docs="`for i in ${install_docs}; do echo $i; done | sort -u`"
export test_rule=check
if [ -z "$SIG" ]; then
  export SIG=0	# set to 1 to turn on signing by default
fi
# Sort in POSIX order.
export LC_ALL=C

# helper functions

# Provide help.
help() {
cat <<EOF
This is the cygwin packaging script for ${FULLPKG}.
Usage: $0 <action>
Actions are:
    help, --help	Print this message
    version, --version	Print the version message
    prep		Unpack and patch into ${srcdir}
    mkdirs		Make hidden directories needed during build
    build, make		Build the package (make)
    clean		Remove built files (make clean)
    install		Install package to staging area (make install)
    list		List package contents
    depend		List package dependencies
    strip		Strip package executables
    pkg, package	Prepare the binary package ${bin_pkg_name}
    mkpatch		Prepare the patch file ${src_patch_name}
    acceptpatch		Apply a patch to the source
    spkg, src-package	Prepare the source package ${src_pkg_name}
    finish		Remove source directory ${srcdir}
    first		Full run for spkg (mkdirs, spkg, finish)
    almostall		Full run for bin pkg, except for finish
    all			Full run for bin pkg
EOF
}

# Provide version of generic-build-script modified to make this
version() {
    vers=`echo '$Revision$' | sed -e 's/Revision: //' -e 's/ *\\$//g'`
    echo "$0 based on generic-build-script $vers"
}

# unpacks the original package source archive into ./${BASEPKG}/
# change this if the original package was not tarred
# or if it doesn't unpack to a correct directory
unpack() {
  tar xv${opt_decomp}f "$1"
}

mkdirs() {
  (cd ${topdir} && \
  rm -fr ${objdir} ${instdir} ${srcinstdir} && \
  mkdir -p ${objdir} && \
  mkdir -p ${instdir} && \
  mkdir -p ${srcinstdir} )
}
prep() {
  (cd ${topdir} && \
  unpack ${src_orig_pkg} && \
  cd ${topdir} && \
  if [ -f ${src_patch} ] ; then \
    patch -Z -p0 < ${src_patch} ;\
  fi && \
  mkdirs )
}

build() {
  (cd ${srcdir} && \
  make -f Makefile.cygwin-sh)
}

clean() {
  (cd ${srcdir} && \
  make -f Makefile.cygwin-sh clean )
}

install() {
  (cd ${srcdir} && \
  rm -fr ${instdir}/* && \
  make -f Makefile.cygwin-sh install DESTDIR=${instdir} && \
  for f in ${prefix}/share/info/dir ${prefix}/info/dir ; do \
    if [ -f ${instdir}${f} ] ; then \
      rm -f ${instdir}${f} ; \
    fi ;\
  done &&\
  for d in ${prefix}/share/doc/${SHORTPKG} ${prefix}/share/doc/Cygwin ; do \
    if [ ! -d ${instdir}${d} ] ; then \
      mkdir -p ${instdir}${d} ;\
    fi ;\
  done &&\
  if [ -d ${instdir}${prefix}/share/info ] ; then \
    find ${instdir}${prefix}/share/info -name "*.info" | xargs -r gzip -q ; \
  fi && \
  if [ -d ${instdir}${prefix}/share/man ] ; then \
    find ${instdir}${prefix}/share/man -name "*.1" -o -name "*.3" -o \
      -name "*.3x" -o -name "*.3pm" -o -name "*.5" -o -name "*.6" -o \
      -name "*.7" -o -name "*.8" | xargs -r gzip -q ; \
  fi && \
  templist="" && \
  for fp in ${install_docs} ; do \
    case "$fp" in \
      */) templist="$templist `cd ${srcdir} && find $fp -type f`" ;;
      *)  for f in ${srcdir}/$fp ; do \
            if [ -f $f ] ; then \
              templist="$templist $f"; \
            fi ; \
          done ;; \
    esac ; \
  done && \
  if [ ! "x$templist" = "x" ]; then \
    /usr/bin/install -m 644 $templist \
         ${instdir}${prefix}/share/doc/${SHORTPKG} ; \
  fi && \
  if [ -f ${srcdir}/CYGWIN-PATCHES/${PKG}.README ]; then \
    /usr/bin/install -m 644 ${srcdir}/CYGWIN-PATCHES/${PKG}.README \
      ${instdir}${prefix}/share/doc/Cygwin/${SHORTPKG}.README ; \
  elif [ -f ${srcdir}/CYGWIN-PATCHES/README ] ; then \
    /usr/bin/install -m 644 ${srcdir}/CYGWIN-PATCHES/README \
      ${instdir}${prefix}/share/doc/Cygwin/${SHORTPKG}.README ; \
  fi && \
  if [ -f ${srcdir}/CYGWIN-PATCHES/${PKG}.sh ] ; then \
    if [ ! -d ${instdir}${sysconfdir}/postinstall ]; then \
      mkdir -p ${instdir}${sysconfdir}/postinstall ; \
    fi && \
    /usr/bin/install -m 755 ${srcdir}/CYGWIN-PATCHES/${PKG}.sh \
      ${instdir}${sysconfdir}/postinstall/${PKG}.sh ; \
  elif [ -f ${srcdir}/CYGWIN-PATCHES/postinstall.sh ] ; then \
    if [ ! -d ${instdir}${sysconfdir}/postinstall ]; then \
      mkdir -p ${instdir}${sysconfdir}/postinstall ; \
    fi && \
    /usr/bin/install -m 755 ${srcdir}/CYGWIN-PATCHES/postinstall.sh \
      ${instdir}${sysconfdir}/postinstall/${PKG}.sh ; \
  fi && \
  if [ -f ${srcdir}/CYGWIN-PATCHES/preremove.sh ] ; then \
    if [ ! -d ${instdir}${sysconfdir}/preremove ]; then \
      mkdir -p ${instdir}${sysconfdir}/preremove ; \
    fi && \
    /usr/bin/install -m 755 ${srcdir}/CYGWIN-PATCHES/preremove.sh \
      ${instdir}${sysconfdir}/preremove/${PKG}.sh ; \
  fi &&
  if [ -f ${srcdir}/CYGWIN-PATCHES/manifest.lst ] ; then
    if [ ! -d ${instdir}${sysconfdir}/preremove ]; then
      mkdir -p ${instdir}${sysconfdir}/preremove ;
    fi &&
    /usr/bin/install -m 755 ${srcdir}/CYGWIN-PATCHES/manifest.lst \
      ${instdir}${sysconfdir}/preremove/${PKG}-manifest.lst ;
  fi )
}
strip() {
  (cd ${instdir} && \
  find . -name "*.dll" -or -name "*.exe" | xargs -r strip 2>&1 ; \
  true )
}
list() {
  (cd ${instdir} && \
  find . -name "*" ! -type d | sed 's%^\.%  %' | sort ; \
  true )
}
depend() {
  (cd ${instdir} && \
  find ${instdir} -name "*.exe" -o -name "*.dll" | xargs -r cygcheck | \
  sed -e '/\.exe/d' -e 's,\\,/,g' | sort -bu | xargs -r -n1 cygpath -u \
  | xargs -r cygcheck -f | sed 's%^%  %' | sort -u ; \
  true )
}
pkg() {
  (cd ${instdir} && \
  tar cvjf ${bin_pkg} * )
}
mkpatch() {
  (cd ${srcdir} && \
  find . -name "autom4te.cache" | xargs -r rm -rf ; \
  unpack ${src_orig_pkg} && \
  mv ${BASEPKG} ../${BASEPKG}-orig && \
  cd ${topdir} && \
  diff -urN -x '.build' -x '.inst' -x '.sinst' \
    ${BASEPKG}-orig ${BASEPKG} > \
    ${srcinstdir}/${src_patch_name} ; \
  rm -rf ${BASEPKG}-orig )
}
# Note: maintainer-only functionality
acceptpatch() {
  cp --backup=numbered ${srcinstdir}/${src_patch_name} ${topdir}
}
spkg() {
  (mkpatch && \
  if [ "${SIG}" -eq 1 ] ; then \
    name=${srcinstdir}/${src_patch_name} text="PATCH" sigfile ; \
  fi && \
  cp ${src_orig_pkg} ${srcinstdir}/${src_orig_pkg_name} && \
  if [ -e ${src_orig_pkg}.sig ] ; then \
    cp ${src_orig_pkg}.sig ${srcinstdir}/ ; \
  fi && \
  cp $0 ${srcinstdir}/`basename $0` && \
  name=$0 text="SCRIPT" sigfile && \
  if [ "${SIG}" -eq 1 ] ; then \
    cp $0.sig ${srcinstdir}/ ; \
  fi && \
  cd ${srcinstdir} && \
  tar cvjf ${src_pkg} * )
}
finish() {
  rm -rf ${srcdir}
}
sigfile() {
  if [ \( "${SIG}" -eq 1 \) -a \( -e $name \) -a \( \( ! -e $name.sig \) -o \( $name -nt $name.sig \) \) ]; then \
    if [ -x /usr/bin/gpg ]; then \
      echo "$text signature need to be updated"; \
      rm -f $name.sig; \
      /usr/bin/gpg --detach-sign $name; \
    else \
      echo "You need the gnupg package installed in order to make signatures."; \
    fi; \
  fi
}
while test -n "$1" ; do
  case $1 in
    help|--help)	help ; STATUS=$? ;;
    version|--version)	version ; STATUS=$? ;;
    prep)		prep ; STATUS=$? ;;
    mkdirs)		mkdirs ; STATUS=$? ;;
    reconf)		reconf ; STATUS=$? ;;
    build)		build ; STATUS=$? ;;
    make)		build ; STATUS=$? ;;
    clean)		clean ; STATUS=$? ;;
    install)		install ; STATUS=$? ;;
    list)		list ; STATUS=$? ;;
    depend)		depend ; STATUS=$? ;;
    strip)		strip ; STATUS=$? ;;
    package)		pkg ; STATUS=$? ;;
    pkg)		pkg ; STATUS=$? ;;
    mkpatch)		mkpatch ; STATUS=$? ;;
    acceptpatch)	acceptpatch ; STATUS=$? ;;
    src-package)	spkg ; STATUS=$? ;;
    spkg)		spkg ; STATUS=$? ;;
    finish)		finish ; STATUS=$? ;;
    first)		mkdirs && spkg && finish ; STATUS=$? ;;
    almostall)		prep && build && install && \
			strip && pkg && spkg ; STATUS=$? ;;
    all)		prep && build && install && \
			strip && pkg && spkg && finish ; STATUS=$? ;;
    *) echo "Error: bad arguments" ; exit 1 ;;
  esac
  ( exit ${STATUS} ) || exit ${STATUS}
  shift
done
