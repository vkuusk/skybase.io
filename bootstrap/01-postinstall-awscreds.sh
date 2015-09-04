#!/usr/bin/env bash

USER=vagrant

mkdir -p /home/$USER/.aws

cat > /home/$USER/.aws/config<<EOF
[profile default]
aws_access_key_id = [[AWS_ACCESS_KEY_ID]]
aws_secret_access_key = [[AWS_SECRET_ACCESS_KEY]]
EOF

chown -R $USER:$USER /home/$USER/.aws

ln -s /home/$USER/.aws/config /etc/skybase/credentials/aws/config
