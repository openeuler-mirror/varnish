Name:             varnish
Summary:          A web application accelerator
Version:          7.0.1
Release:          6
License:          BSD
URL:              https://www.varnish-cache.org/
Source0:          http://varnish-cache.org/_downloads/varnish-%{version}.tgz

# https://github.com/varnishcache/pkg-varnish-cache
Source1:          https://github.com/varnishcache/pkg-varnish-cache/archive/0ad2f22629c4a368959c423a19e352c9c6c79682/pkg-varnish-cache-0ad2f22.tar.gz
Patch0001:        fix-varnish-devel-installation-failure.patch
Patch0002:        fix-varnish.service-reload-failed.patch
#https://github.com/varnishcache/varnish-cache/commit/fceaefd4d59a3b5d5a4903a3f420e35eb430d0d4
Patch0003:        CVE-2022-23959.patch
Patch0004:        CVE-2022-38150.patch

BuildRequires:    python3-sphinx python3-docutils pkgconfig make graphviz nghttp2 systemd-units
BuildRequires:    ncurses-devel pcre2-devel libedit-devel gcc
Requires:         logrotate ncurses pcre2 jemalloc openEuler-rpm-config gcc
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

# No idea why these ends up with mode 600 in the debug package
%if 0%{debug_package}
chmod 644 lib/libvmod_*/*.c
chmod 644 lib/libvmod_*/*.h
%endif

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
%exclude /usr/lib/debug/*
%exclude /usr/src/debug/*
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
* Tue Aug 23 2022 jiangpeng <jiangpeng01@ncti-gba.cn> - 7.0.1-6
- Fix CVE-2022-38150

* Tue Apr 26 2022 yaoxin <yaoxin30@h-partners.com> - 7.0.1-5
- Fix CVE-2022-23959

* Fri Mar 04 2022 houyingchao <houyingchao@huawei.com> - 7.0.1-4
- Strip binary files

* Fri Feb 18 2022 caodongxia <caodongxia@huawei.com> - 7.0.1-3
- Fix varnish.service reload failed due to miss conf

* Fri Jan 21 2021 wulei <wulei80@huawei.com> - 7.0.1-2
- Fix varnish-devel installation failure

* Wed Dec 29 2021 yaoxin <yaoxin30@huawei.com> - 7.0.1-1
- Upgrade varnish to 7.0.1

* Wed Sep 22 2021 yaoxin <yaoxin30@huawei.com> - 6.0.0-8
- Fix CVE-2021-36740

* Mon May 31 2021 huanghaitao <huanghaitao8@huawei.com> - 6.0.0-7
- Completing build dependencies to fix gcc compiler missing error

* Tue Jan 19 2021 wangyue <wangyue92@huawei.com> - 6.0.0-6
- Fix CVE-2019-15892

* Tue Jun 2 2020 chengzihan <chengzihan2@huawei.com> - 6.0.0-5
- Fix the error of using parameter ("%s", NULL) for 'printf' when built by gcc-9

* Mon Feb 10 2020 wangye <wangye54@huawei.com> - 6.0.0-4
- Init package
