#!/usr/bin/env bash
# optional and manual post-installation script to setup skybase credentials

USER=$1
SECRET=$2

SKYBASE_USER_GROUP_DEFAULT=vagrant

# TODO: remove --secret option; exec user.list -u $USER and filter for auto-generated secret and write to credentials file
sky user add --username $USER --role admin --secret $SECRET --apply -m local

mkdir -p /home/$SKYBASE_USER_GROUP_DEFAULT/.skybase
cat > /home/$SKYBASE_USER_GROUP_DEFAULT/.skybase/credentials.yaml<<EOF
user_id: $USER
key: $SECRET
EOF

chown -R $SKYBASE_USER_GROUP_DEFAULT:$SKYBASE_USER_GROUP_DEFAULT /home/$SKYBASE_USER_GROUP_DEFAULT/.skybase
