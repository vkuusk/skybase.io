Skybase Developer Guide
=======================

prerequisites
-------------
1. amazon web services account
2. github account
3. python 2.7 (python-dev?)
4. pip
5. git
6. sqlite3
7. virtualenv, virtualenvwrapper (recommended)
8. aws cli (recommended)
9. vagrant (recommended)

local installation
------------------
1. cd /path/to/skybase/app; export SKYBASE_SOURCE=/path/to/skybase/app
2. pip install skybase
    * git clone git@github.com:lithiumtech/skybase.io.git
3. pip install -r $SKYBASE_SOURCE/requirements.txt

4. create external application directories
    * mkdir -p /var/log/skybase
    * mkdir -p /etc/skybase/credentials/{aws,chef,salt}
    * mkdir -p /srv/skybase/data/{celery,dbauth,dbstate,artiballs}
    * mkdir -p /srv/skybase/credentials/aws
    
5. copy configuration and sample planet and template files
    * cp $SKYBASE_SOURCE/config/* /etc/skybase
    * cp -r $SKYBASE_SOURCE/examples/planets/*   /srv/skybase/data/planets
    * cp -r $SKYBASE_SOURCE/examples/templates/* /srv/skybase/data/templates
    * cp -r $SKYBASE_SOURCE/examples/artiballs/* /srv/skybase/data/artiballs
    * cp -r $SKYBASE_SOURCE/scripts/* /usr/local/bin

6. verify installation
    * sky --help
    
post-installation
-----------------
1. create AWS config file
    * $SKYBASE_SOURCE/bootstrap/01-postinstall-awscreds.sh
    * vi ~/.aws/config and substitute your AWS key and secret
    * ln -s ~/.aws/config /etc/skybase/credentials/aws/config
    
2. (optional) establish skybase credentials for restapi mode
    * $SKYBASE_SOURCE/bootstrap/02-postinstall-authdb.sh
    
3. use or generate AWS key pair for reference in deployment templates


configuration
-------------
1. gather the following required values
    * account profile ('default' typical for private accounts)
    * VPC id (aws ec2 describe-vpcs --region us-west-1)
    * Subnet ids (aws ec2 describe-vpcs --region us-west-1)
2. create S3 buckets for the following values
    * object-store-releasebundles
    * yumrepo
    * prov-object-store
    * yumrepo-3rd-party
3. replace planet variables in yaml file with derived values: profile, VPC, Subnets, Buckets
    * {{ profile }}
    * {{ bucket_object-store-releasebundles }}
    * {{ bucket_yumrepo }}
    * {{ bucket_prov-object-store }}
    * {{ bucket_yumrepo-3rd-party }}
    * {{ vpc_id }}
    * {{ subnet_us_west_1a }}
    * {{ subnet_us_west_1c }}
4. verify planet configuration
    * sky route ping -m local

service1 deployment
-------------------
1. gather the following required values
    * AWS key pair ( aws ec2 create-key-pair --key-name YOUR_KEY_NAME --region us-west-1)
    * Team ID for tagging instance
    * Email address for tagging
2. Using previous, replace the following values in examples/service1/deployment/main_deployment.yaml
    * {{ keyname }}
    * {{ teamid }}
    * {{ email }}
3. package an artiball
    * sky pack clean
    * sky pack validate
    * export AB=$(sky pack create)
    * sky pack upload
    * sky pack submit --artiball $AB
4. deploy artiball to AWS
    * sky service deploy --mode local --planet dev-aws-us-west-1 --artiball $AB --tag TEST --apply
5. check status of deployment
    * sky service status --planet dev-aws-us-west-1 --mode local --verbose
6. delete stack
    *  sky service delete-stacks --planet dev-aws-us-west-1 --service service1 --tag TEST --mode local --delete-all-stacks --apply


vagrant installation
--------------------
install skybase using a vagrant "ubuntu/trusty64" instance.  

prerequisites
-------------
1. [vagrant](https://www.vagrantup.com/)

installation
------------
1. pip install or clone skybase.io repos on localhost to be shared with vagrant guest  
2. cd skybase.io
3. export SKYBASE_HOME=`pwd`
4. cd $SKYBASE_HOME/bootstrap
5. vagrant up
6. vagrant ssh
7. follow post-installation, configuration and service1 steps listed above

        


