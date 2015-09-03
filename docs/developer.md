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
(1) build/populate directories