# This is the PostgreSQL Global Development Group Official RPMset spec file,
# or a derivative thereof.
# Copyright 2003-2009 Lamar Owen <lowen@pari.edu> <lamar.owen@wgcr.org>
# and others listed.                 ** vi: ts=4 sw=4 noexpandtab nosmarttab

# Major Contributors:
# ---------------
# Lamar Owen
# Trond Eivind Glomsrd <teg@redhat.com>
# Thomas Lockhart
# Reinhard Max
# Karl DeBisschop
# Peter Eisentraut
# Joe Conway
# Andrew Overholt
# David Jee
# Kaj J. Niemi
# Sander Steffann
# Tom Lane
# and others in the Changelog....

# This spec file and ancillary files are licensed in accordance with
# The PostgreSQL license.

# In this file you can find the default build package list macros.
# These can be overridden by defining on the rpm command line:
# rpm --define 'packagename 1' .... to force the package to build.
# rpm --define 'packagename 0' .... to force the package NOT to build.
# The base package, the libs package, the devel package, and the server package
# always get built.

%{!?beta:%global beta 0}

%{!?test:%global test 1}
%{!?upgrade:%global upgrade 1}
%{!?plpython:%global plpython 1}
%{!?plpython3:%global plpython3 1}
%{!?pltcl:%global pltcl 1}
%{!?plperl:%global plperl 1}
%{!?ssl:%global ssl 1}
%{!?kerberos:%global kerberos 1}
%{!?ldap:%global ldap 1}
%{!?nls:%global nls 1}
%{!?uuid:%global uuid 1}
%{!?xml:%global xml 1}
%{!?pam:%global pam 1}
%{!?sdt:%global sdt 1}
%{!?selinux:%global selinux 1}
%{!?runselftest:%global runselftest 1}

# By default, patch(1) creates backup files when chunks apply with offsets.
# Turn that off to ensure such files don't get included in RPMs.
%global _default_patch_flags --no-backup-if-mismatch

# https://fedoraproject.org/wiki/Packaging:Guidelines#Packaging_of_Additional_RPM_Macros
%global macrosdir %(d=%{_rpmconfigdir}/macros.d; [ -d $d ] || d=%{_sysconfdir}/rpm; echo $d)

%global majorversion 9.6

Summary: PostgreSQL upgrade from %majorversion
Name: postgresql-upgrade96
Version: 9.6.15
Release: 1%{?dist}

# The PostgreSQL license is very similar to other MIT licenses, but the OSI
# recognizes it as an independent license, so we do as well.
License: PostgreSQL
Group: Applications/Databases
Url: http://www.postgresql.org/

%global pkg_prefix %{_libdir}/pgsql/postgresql-%{majorversion}
%global precise_version %{?epoch:%epoch:}%version-%release

Source0: https://ftp.postgresql.org/pub/source/v%{version}/postgresql-%{version}.tar.bz2
Source4: Makefile.regress

# Those here are just to enforce packagers check that the tarball was downloaded
# correctly.  Also, this allows us check that packagers-only tarballs do not
# differ with publicly released ones.
Source1: https://ftp.postgresql.org/pub/source/v%{version}/postgresql-%{version}.tar.bz2.sha256

# Comments for these patches are in the patch files.
Patch1: rpm-pgsql.patch
Patch2: postgresql-logging.patch
Patch5: postgresql-var-run-socket.patch
Patch6: postgresql-man.patch

BuildRequires: gcc
BuildRequires: perl(ExtUtils::MakeMaker) glibc-devel bison flex gawk
BuildRequires: perl(ExtUtils::Embed), perl-devel
%if 0%{?fedora} || 0%{?rhel} > 7
BuildRequires: perl-generators
%endif
BuildRequires: readline-devel zlib-devel
BuildRequires: systemd systemd-devel util-linux
BuildRequires: multilib-rpm-config

%if %ssl
BuildRequires: openssl-devel
%endif

%if %kerberos
BuildRequires: krb5-devel
%endif

%if %ldap
BuildRequires: openldap-devel
%endif

%if %nls
BuildRequires: gettext >= 0.10.35
%endif

%if %uuid
BuildRequires: uuid-devel
%endif

%if %xml
BuildRequires: libxml2-devel libxslt-devel
%endif

%if %pam
BuildRequires: pam-devel
%endif

%if %sdt
BuildRequires: systemtap-sdt-devel
%endif

%if %selinux
BuildRequires: libselinux-devel
%endif

# https://bugzilla.redhat.com/1464368
%global __provides_exclude_from %{_libdir}/pgsql

%description
PostgreSQL is an advanced Object-Relational database management system (DBMS).
The postgresql-upgrade* package contains the deamon of the particular version
that is necessary for upgrading from this verison using pg_upgrade utility and
supporting files needed for upgrading.

%package devel
Summary: Support for build of extensions required for upgrade process
Group: Development/Libraries
Requires: %{name}-upgrade%{?_isa} = %precise_version

%description devel
The postgresql-devel package contains the header files and libraries
needed to compile C or C++ applications which are necessary in upgrade
process.


%prep
(
  cd "$(dirname "%{SOURCE0}")"
  sha256sum -c %{SOURCE1}
)
%setup -q -n postgresql-%{version}
%patch1 -p1
#%patch2 -p1
%patch5 -p1
%patch6 -p1

# We used to run autoconf here, but there's no longer any real need to,
# since Postgres ships with a reasonably modern configure script.

# remove .gitignore files to ensure none get into the RPMs (bug #642210)
find . -type f -name .gitignore | xargs rm


%build
# fail quickly and obviously if user tries to build as root
%if %runselftest
	if [ x"`id -u`" = x0 ]; then
		echo "postgresql's regression tests fail if run as root."
		echo "If you really need to build the RPM as root, use"
		echo "--define='runselftest 0' to skip the regression tests."
		exit 1
	fi
%endif

# Fiddling with CFLAGS.

CFLAGS="${CFLAGS:-%optflags}"
%ifarch %{power64}
# See the bug #1051075, ppc64 should benefit from -O3
CFLAGS=`echo $CFLAGS | xargs -n 1 | sed 's|-O2|-O3|g' | xargs -n 100`
%endif
# Strip out -ffast-math from CFLAGS....
CFLAGS=`echo $CFLAGS|xargs -n 1|grep -v ffast-math|xargs -n 100`
export CFLAGS

# The upgrade build can be pretty stripped-down, but make sure that
# any options that affect on-disk file layout match the previous
# major release!

# The set of built server modules here should ideally create superset
# of modules we used to ship in %%prevversion (in the installation
# the user will upgrade from), including *-contrib or *-pl*
# subpackages.  This increases chances that the upgrade from
# %%prevversion will work smoothly.


upgrade_configure ()
{
	# Note we intentionally do not use %%configure here, because we *don't* want
	# its ideas about installation paths.

	# The -fno-aggressive-loop-optimizations is hack for #993532
	PYTHON="${PYTHON-/usr/bin/python3}" \
	CFLAGS="$CFLAGS -fno-aggressive-loop-optimizations" ./configure \
		--build=%{_build} \
		--host=%{_host} \
		--prefix=%pkg_prefix \
		--disable-rpath \
		--with-system-tzdata=/usr/share/zoneinfo \
		"$@"
}

upgrade_configure

make %{?_smp_mflags} all
make -C contrib %{?_smp_mflags} all


%install
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/postgresql-setup/upgrade/
cat > $RPM_BUILD_ROOT%{_sysconfdir}/postgresql-setup/upgrade/postgresql-96.conf <<EOF
id              postgresql-96
major           %{majorversion}
data_default    %{_localstatedir}/lib/pgsql/data
package         %{name}
engine          %{_libdir}/pgsql/postgresql-%{majorversion}/bin
description     "Upgrade data from system PostgreSQL version (PostgreSQL %{majorversion})"
redhat_sockets_hack no
EOF

make DESTDIR=$RPM_BUILD_ROOT install
make -C contrib DESTDIR=$RPM_BUILD_ROOT install

# remove stuff we don't actually need for upgrade purposes
pushd $RPM_BUILD_ROOT%{_libdir}/pgsql/postgresql-%{majorversion}
rm bin/clusterdb
rm bin/createdb
rm bin/createlang
rm bin/createuser
rm bin/dropdb
rm bin/droplang
rm bin/dropuser
rm bin/ecpg
rm bin/initdb
rm bin/pg_basebackup
rm bin/pg_dump
rm bin/pg_dumpall
rm bin/pg_restore
rm bin/pgbench
rm bin/psql
rm bin/reindexdb
rm bin/vacuumdb
rm -rf share/doc
rm -rf share/man
rm -rf share/tsearch_data
rm lib/*.a
# Drop libpq.  This might need some tweaks once there's
# soname bump between %%prevversion and %%version.
rm lib/libpq.so*
# Drop libraries.
rm lib/lib{ecpg,ecpg_compat,pgtypes}.so*
rm share/*.bki
rm share/*description
rm share/*.sample
rm share/*.sql
rm share/*.txt
rm share/extension/*.sql
rm share/extension/*.control
popd

mkdir -p $RPM_BUILD_ROOT%macrosdir
cat <<EOF > $RPM_BUILD_ROOT%macrosdir/macros.%name
%%postgresql_upgrade_prefix %pkg_prefix
EOF


%files
%config %{_sysconfdir}/postgresql-setup/upgrade/*.conf
%{_libdir}/pgsql/postgresql-%{majorversion}/bin
%exclude %{_libdir}/pgsql/postgresql-%{majorversion}/bin/pg_config
%{_libdir}/pgsql/postgresql-%{majorversion}/lib
%exclude %{_libdir}/pgsql/postgresql-%{majorversion}/lib/pgsql/pgxs
%exclude %{_libdir}/pgsql/postgresql-%{majorversion}/lib/pkgconfig
%{_libdir}/pgsql/postgresql-%{majorversion}/share


%files devel
%{_libdir}/pgsql/postgresql-%{majorversion}/bin/pg_config
%{_libdir}/pgsql/postgresql-%{majorversion}/include
%{_libdir}/pgsql/postgresql-%{majorversion}/lib/pkgconfig
%{_libdir}/pgsql/postgresql-%{majorversion}/lib/pgsql/pgxs/

%{macrosdir}/macros.%name


%changelog
* Tue Aug 13 2019 Honza Horak <hhorak@redhat.com> - 9.6.15-1
- Iniial packaging of the upgrade package, taken from postgresql spec
