#!/usr/bin/env bash

SKYBASE_SOURCE=$1
echo "SKYBASE_SOURCE ==> $SKYBASE_SOURCE"


# pip installation.  not using apt-get due to possible trusty bug with requests:
# https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1306991
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py

pip install -r $SKYBASE_SOURCE/requirements.txt
pip install awscli

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
    chmod -R 777 /etc/skybase
    cp $SKYBASE_SOURCE/config/* /etc/skybase
fi

if [ ! -d "/srv/skybase" ]; then

    mkdir -p /srv/skybase/data/{celery,dbauth,dbstate,artiballs}
    chmod -R 777 /srv/skybase

    cd /srv/skybase/data
    ln -s $SKYBASE_SOURCE/data/planets
    ln -s $SKYBASE_SOURCE/data/templates
    ln -s $SKYBASE_SOURCE/data/artiballs

fi

cd /usr/local/bin

ln -s $SKYBASE_SOURCE/scripts/sky || true
ln -s $SKYBASE_SOURCE/scripts/sky-restapi || true
ln -s $SKYBASE_SOURCE/scripts/sky-worker || true

# convienience for viewing skybase results
cat >> .profile<<EOF
alias pj='python -m json.tool'
EOF

# setup python env
echo "export PYTHONPATH=$SKYBASE_SOURCE" >> /home/vagrant/.profile

# sky route ping -local should work
# copy planet, template, artiball data from examles (deprecate links above)
# 01-postinstall-awscreds.sh
# vi ~/.aws/config and replace id, secret

