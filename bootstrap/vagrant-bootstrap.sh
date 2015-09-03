#!/usr/bin/env bash

# pip installation.  not using apt-get due to possible trusty bug with requests:
# https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1306991
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py

### skybase ###
# add directories

apt-get update -y
apt-get install -y python-dev git sqlite3

if [ ! -d "/var/log/skybase" ]; then
    mkdir -p /var/log/skybase
    chmod 777 /var/log/skybase
fi

if [ ! -d "/etc/skybase" ]; then
    mkdir -p /etc/skybase/credentials/{aws,chef,salt}
    chmod -R 755 /etc/skybase
fi

if [ ! -d "/srv/skybase" ]; then
    mkdir -p /srv/skybase/data/{celery,dbauth,dbstate,artiballs,planets,templates}
    mkdir -p /srv/skybase/credentials/aws
    chmod -R 775 /srv/skybase
fi

cd /usr/local/bin

ln -s /opt/skybase/scripts/sky
ln -s /opt/skybase/scripts/sky-restapi
ln -s /opt/skybase/scripts/sky-worker

pip install -r /opt/skybase/requirements.txt

# convienience for viewing skybase results
cat >> .profile<<EOF
alias pj='python -m json.tool'
EOF
