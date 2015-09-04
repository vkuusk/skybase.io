Skybase Developer Guide
=======================

prerequisites
-------------
0. amazon web services account
1. github account


vagrant installation
--------------------
**prerequisites**

0. [vagrant](https://www.vagrantup.com/)

**installation**

1. pip install or clone skybase.io repos on localhost to be shared with vagrant guest  
1. cd skybase.io
1. export SKYBASE_HOME=`pwd`
1. d $SKYBASE_HOME/bootstrap
1. vagrant up
1. vagrant ssh

**post-installation**

1. ./01-postinstall-awscreds.sh
1. revise ~/.aws/config providing your AWS API keys
1. ./02-postinstall-authdb.sh (skybase credentials required only for restapi server mode)
    * TODO: move postinstall bootstrap scripts to executable directory)
1. revise data/planet/dev-aws-us-west-1.yaml
    1. account profile
    1. vpc and subnet ids
    1. s3 buckets: 

localhost installation
----------------------
**prerequisites**

1. python2.7
2. pip
3. virtualenv, virtualenvwrapper (recommended)
3. git
4. awscli (optional)
5. vagrant (only if using Vagrantfile)
1. pip install -r requirements.txt
   * TODO: link to separate document identifying steps from vagrant-bootstrap.sh

planets
-------
data/planets
(1) identify default AWS VPC: aws ec2 describe-vpcs
(2) enter into planet yaml: resource_ids.vpc_id: [["vpc-0123456"]]


templates
---------
data/templates  
TODO: add simple ec2 instance template (no ASG)

bootstrap process
-----------------
(1) vagrant up
(2) generate aws config
(3) add personal 
(3) skybase credentials
(4) AWS S3
(4) planet configuration
    (a) vpc_id <== aws ec2 describe-vpcs --region us-west-1
    (b) subnets <== aws ec2 describe-subnets --region us-west-1
    (c) s3 buckets:
        object-store-releasebundles <== aws s3 mb s3://skybase-nonprod-artiballs 
        yumrepo <== aws s3 mb s3://skybase-repo-nonprod-us-west-1
        prov-object-store <== aws s3 mb s3://skybase-provision
        yumrepo-3rd-party <== aws s3 mb s3://skybase-repo-3rd-party-us-west-1
(5) service1 preparation
    (a) generate key-pair <== aws ec2 create-key-pair --key-name skybase-io --region us-west-1
    (b) revise/edit deployment/main_deployment.yaml
        definition: keyname: <keypair>
        


