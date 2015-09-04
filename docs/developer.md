Skybase Developer Guide
=======================

python
------
pip install -r requirements.txt

planets
-------
examples/dev-aws-us-west-1
(1) identify default AWS VPC: aws ec2 describe-vpcs
(2) enter into planet yaml: resource_ids.vpc_id: [["vpc-0123456"]]

configuration
-------------
(1) requires AWS Account Profile Name/ID

bootstrap
---------
(1) vagrant up
(2) aws credentials
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
        


