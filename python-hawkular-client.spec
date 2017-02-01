%global srcname hawkular-client
%global _docdir_fmt %{name}

%if 0%{?fedora}
%bcond_without python3
%else
%bcond_with python3
%endif

Name:           python-%{srcname}
Version:        0.5.1
Release:        1%{?dist}
Summary:        Python client to communicate with Hawkular server over HTTP(S)

License:        ASL 2.0
URL:            https://github.com/google/%{srcname}
Source0:        https://pypi.python.org/packages/source/h/%{srcname}/%{srcname}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python2-pypandoc
## For tests
#BuildRequires:  python-mox
#Requires:       python-dateutil
#Requires:       python-gflags
#Requires:       pytz

%description
Python client to access Hawkular-Metrics, an abstraction to invoke REST-methods 
on the server endpoint using urllib2. No external dependencies.


%if %{with python3}
%package -n python3-%{srcname}
Summary:        Python 3 client to communicate with Hawkular server over HTTP(S)
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python-tools
BuildRequires:  python3-pypandoc
# For tests
# python-mox doesn't work with python3
# https://bugzilla.redhat.com/show_bug.cgi?id=1209203
#BuildRequires:  python3-mox
Requires:       python3-dateutil
Requires:       python3-gflags
Requires:       python3-pytz

%description -n python3-%{srcname}
Python client to access Hawkular-Metrics, an abstraction to invoke REST-methods 
on the server endpoint using urllib2. No external dependencies.
%endif # with python3

%prep
%setup -qc
mv python-%{srcname}-%{version} python2
%if %{with python3}
cp -a python2 python3
2to3 --write --nobackups python3
%endif # with python3


%build
pushd python2
%{__python2} setup.py build
popd

%if %{with python3}
pushd python3
%{__python3} setup.py build
popd
%endif # with python3


%install
%if %{with python3}
pushd python3
%{__python3} setup.py install --skip-build --root %{buildroot}
popd
%endif # with python3

pushd python2
%{__python2} setup.py install --skip-build --root %{buildroot}
popd


%files
%doc python2/README.rst
%{python2_sitelib}/*

%if %{with python3}
%files -n python3-%{srcname}
%doc python3/README.rst
%{python3_sitelib}/*
%endif # with python3

%changelog
* Tue Jan 24 2017 Troy Dawson <tdawson@redhat.com> - 0.5.1-1
- Update to 0.5.1

* Thu Jan 12 2017 Troy Dawson <tdawson@redhat.com> - 0.5.0-1
- Update to 0.5.0

* Tue Sep 20 2016 Troy Dawson <tdawson@redhat.com> - 0.4.5-1
- Initial package
