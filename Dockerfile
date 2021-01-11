FROM centos:8

ARG NAGIOS_VERSION=4.0.8
ARG NAGION_PREFIX=4.x
ARG NAGIOS_PLUGINS_VERSION=2.0.3
ARG ILERT_PLUGIN_VERSION=1.5

RUN set -ex; \
    yum -y update; \
    yum -y install epel-release gd gd-devel wget httpd php gcc make perl tar python2; \
    adduser nagios; \
    groupadd nagcmd; \
    usermod -a -G nagcmd nagios

ADD http://downloads.sourceforge.net/project/nagios/nagios-${NAGION_PREFIX}/nagios-${NAGIOS_VERSION}/nagios-${NAGIOS_VERSION}.tar.gz nagios-${NAGIOS_VERSION}.tar.gz
ADD http://www.nagios-plugins.org/download/nagios-plugins-${NAGIOS_PLUGINS_VERSION}.tar.gz nagios-plugins-${NAGIOS_PLUGINS_VERSION}.tar.gz
ADD https://github.com/iLert/ilert-nagios/archive/v${ILERT_PLUGIN_VERSION}.zip ilert-nagios-v${ILERT_PLUGIN_VERSION}.zip

RUN set -ex; \
    ln -s /usr/bin/python2 /usr/bin/python; \
    unzip ilert-nagios-v${ILERT_PLUGIN_VERSION}.zip; \
    ls -la; \
    mv ilert-nagios-${ILERT_PLUGIN_VERSION}/ilert_nagios.py /usr/local/bin/ilert_nagios.py; \
    chmod +x /usr/local/bin/ilert_nagios.py; \
    tar xf nagios-${NAGIOS_VERSION}.tar.gz; \
    cd nagios-${NAGIOS_VERSION} && ./configure --with-command-group=nagcmd; \
    make all && make install && make install-init; \
    make install-config && make install-commandmode && make install-webconf; \
    echo 'admin:admin' > /usr/local/nagios/etc/htpasswd.users; \
    chown nagios:nagios /usr/local/nagios/etc/htpasswd.users; \
    cd ..; \
    tar xf nagios-plugins-${NAGIOS_PLUGINS_VERSION}.tar.gz; \
    cd nagios-plugins-${NAGIOS_PLUGINS_VERSION} && ./configure --with-nagios-user=nagios --with-nagios-group=nagios; \
    make && make install; \
    /usr/local/nagios/bin/nagios -v /usr/local/nagios/etc/nagios.cfg; \
    touch /var/www/html/index.html; \
    chown nagios.nagcmd /usr/local/nagios/var/rw; \
    chmod g+rwx /usr/local/nagios/var/rw; \
    chmod g+s /usr/local/nagios/var/rw

CMD ["/usr/local/nagios/bin/nagios", "/usr/local/nagios/etc/nagios.cfg"]
