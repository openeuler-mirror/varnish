Name:             varnish
Summary:          A web application accelerator
Version:          6.0.0
Release:          6
License:          BSD
URL:              https://www.varnish-cache.org/
Source0:          http://varnish-cache.org/_downloads/varnish-%{version}.tgz

# https://github.com/varnishcache/pkg-varnish-cache
Source1:          https://github.com/varnishcache/pkg-varnish-cache/archive/0ad2f22629c4a368959c423a19e352c9c6c79682/pkg-varnish-cache-0ad2f22.tar.gz

Patch0001:        varnish-5.1.1.fix_ld_library_path_in_doc_build.patch

BuildRequires:    python3-sphinx python3-docutils pkgconfig make graphviz nghttp2 systemd-units
BuildRequires:    ncurses-devel pcre-devel libedit-devel
Requires:         logrotate ncurses pcre jemalloc openEuler-rpm-config gcc
Requires:	  %{name}-help = %{version}-%{release}
Requires(pre):    shadow-utils
Requires(post):   /usr/bin/uuidgen systemd-units systemd-sysv
Requires(preun):  systemd-units
Requires(postun): systemd-units
Obsoletes:        varnish-libs

%description
This is Varnish Cache, a web application accelerator also known as a caching HTTP reverse proxy.
You install it in front of any server that speaks HTTP and configure it to cache the contents.
Varnish Cache is really, really fast. It typically speeds up delivery with a factor of 300 - 1000x,
depending on your architecture.

%package       devel
Summary:       Development files for varnish
BuildRequires: ncurses-devel
Requires:      varnish = %{version}-%{release} python3
Provides:      varnish-libs-devel = %{version}-%{release}
Obsoletes:     varnish-libs-devel

%description   devel
Development files for varnish.
Varnish Cache is a high-performance HTTP accelerator

%package       help
Summary:       Help documentation files for varnish
Requires:      varnish = %{version}-%{release}
Provides:      varnish-docs = %{version}-%{release}
Obsoletes:     varnish-docs < %{version}-%{release}
BuildArch:     noarch

%description   help
Help documentation files for varnish.

%prep
%autosetup -p1 -a 0 -a 1
ln -s pkg-varnish-cache-0ad2f22629c4a368959c423a19e352c9c6c79682/redhat redhat
ln -s pkg-varnish-cache-0ad2f22629c4a368959c423a19e352c9c6c79682/debian debian
cp redhat/find-provides .

%build
export RST2MAN=/bin/true

%configure --disable-static \
%ifarch aarch64
  --with-jemalloc=no \
%endif
  --localstatedir=/var/lib  \
  --docdir="%{_docdir}/varnish"

sed -i 's|^hardcode_libdir_flag_spec=.*|hardcode_libdir_flag_spec=""|g;
        s|^runpath_var=LD_RUN_PATH|runpath_var=DIE_RPATH_DIE|g' libtool

mkdir lib/libvarnishapi/.libs
pushd lib/libvarnishapi/.libs
ln -s libvarnishapi.so libvarnishapi.so.1
popd

%make_build

sed -i 's,User=varnishlog,User=varnish,g;' redhat/varnishncsa.service
sed -i 's/env python/python3/g;' lib/libvcc/vmodtool.py

rm -rf doc/html/_sources

%install
%make_install

find %{buildroot}/%{_libdir}/ -name '*.la' -exec rm -f {} ';'

mkdir -p %{buildroot}/var/lib/varnish
mkdir -p %{buildroot}/var/log/varnish
mkdir -p %{buildroot}/var/run/varnish
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d/
mkdir -p %{buildroot}%{_unitdir}

install -D -m 0644 etc/example.vcl            %{buildroot}%{_sysconfdir}/varnish/default.vcl
install -D -m 0644 redhat/varnish.logrotate   %{buildroot}%{_sysconfdir}/logrotate.d/varnish
install -D -m 0644 include/vcs_version.h      %{buildroot}%{_includedir}/varnish
install -D -m 0644 include/vrt.h              %{buildroot}%{_includedir}/varnish
install -D -m 0644 redhat/varnish.service     %{buildroot}%{_unitdir}/varnish.service
install -D -m 0644 redhat/varnishncsa.service %{buildroot}%{_unitdir}/varnishncsa.service
install -D -m 0755 redhat/varnishreload       %{buildroot}%{_sbindir}/varnishreload

echo %{_libdir}/varnish > %{buildroot}%{_sysconfdir}/ld.so.conf.d/varnish-%{_arch}.conf

chmod 644 lib/libvmod_*/*.c
chmod 644 lib/libvmod_*/*.h

%check
%ifarch aarch64
sed -i 's/48/128/g;' bin/varnishtest/tests/c00057.vtc
%endif
make %{?_smp_mflags} check LD_LIBRARY_PATH="%{buildroot}%{_libdir}:%{buildroot}%{_libdir}/%{name}" VERBOSE=1

%pre
getent group varnish >/dev/null || groupadd -r varnish
getent passwd varnish >/dev/null || \
       useradd -r -g varnish -d /var/lib/varnish -s /sbin/nologin \
               -c "Varnish Cache" varnish
exit 0

%post
%systemd_post varnish.service
/sbin/ldconfig

chown varnish:varnish /var/log/varnish/varnishncsa.log 2>/dev/null || true

test -f /etc/varnish/secret || (uuidgen > /etc/varnish/secret && chmod 0600 /etc/varnish/secret)

%preun
%systemd_preun varnish.service

%files
%license LICENSE
%dir %{_sysconfdir}/varnish/
%attr(0700,varnish,varnish) %dir %{_var}/log/varnish
%{_sbindir}/*
%{_bindir}/*
%{_libdir}/*.so.*
%{_libdir}/varnish
%{_var}/lib/varnish
%config(noreplace) %{_sysconfdir}/varnish/default.vcl
%config(noreplace) %{_sysconfdir}/logrotate.d/varnish
%config %{_sysconfdir}/ld.so.conf.d/varnish-%{_arch}.conf

%{_unitdir}/varnish.service
%{_unitdir}/varnishncsa.service

%files devel
%{_includedir}/varnish
%{_libdir}/lib*.so
%{_libdir}/pkgconfig/varnishapi.pc
%{_datadir}/varnish
%{_datadir}/aclocal/*.m4
%exclude %{_docdir}/varnish/{builtin.vcl,example.vcl}

%files help
%doc doc/html doc/changes*.html README.rst ChangeLog etc/builtin.vcl etc/example.vcl
%{_mandir}/man1/*.1*
%{_mandir}/man3/*.3*
%{_mandir}/man7/*.7*

%changelog
* Mon Nov 9 2020 baizhonggui <baizhonggui@huawei.com> - 6.0.0-5
- Add install requires help package into main package

* Mon Feb 10 2020 wangye <wangye54@huawei.com> - 6.0.0-4
- Init package
