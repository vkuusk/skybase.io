# 1. Introduction.

During this tutorial you will learn basic concepts and operations of the Skybase system.
Note: (smile) It's possible to skip "Introduction" section, BUT then you'll have no idea what the commands in the following section will be doing (smile) So, please, spend 5 min on this section
## 1.1 Basic Concepts
Skybase is a system to automate deployment, updates and management of the deployed services. It makes deployment of services cloud agnostic, i.e. once created the Service Package can be deployed without changes into AWS or Openstack. Additional benefits of using Skybase is simplification of infrastructure configurations ( e.g. subnetID, ImageID, Chef server URLs) and credential management (e.g. AWS, Openstack, Chef creds).
From very high level Skybase operations can be described as "Skybase deploys Services into different destinations and manages these services until they are retired". There are three main concepts (terms) used in Skybase system:
"Service" ( as in SOA ) - This is what we are deploying. "Service" consists of one or more "Stacks". Each "Stack" consists of one or more "Roles". Each "Role" is composed of one or more "Instances"

![alt tag](https://raw.github.com/lithiumtech/skybase.io/master/docs/Service-in-Skybase.png)

Example: Service = 2_Tier_Service;
Stack_1 = "AppServer_Tier";  Role_A = "AppServer"
Stack_2 = "Database_Tier"; Role_X = "DB_Master"; Role_Y = "DB_Slave"
 
"Planet" - Where we deploy a service to.
"Artiball" - Tarball of Artifacts (It's how we package the Service)
It is recommended that you'll read more detailed description of terminology. HERE

## 1.2 Basic Operations
The Goal of this Guide is to walk you through the following:
Installation of the Skybase Client
Configuring your Project's git repo to work with Skybase
Creating a Basic Definition of the Cloud Resources needed to run your service
Packaging your Service and submit it to the Skybase
Basic operations with Service: DEPLOY, get STATUS, DELETE

# 2. Installing Skybase CLI
In this section we will A) install prerequisites and B) install and configure skybase client.
 
## 2.1 Install Prerequisites.
The only dependency for Skybase client itself is Python 2.7, but for some Chef related operations one also will need to install Berkshelf and ChefDK.
This document assumes that you have development environment already setup for working with Chef. If you do not, please follow this wiki: Getting Started Guide - Chef Development
 
sudo /usr/bin/gem install fpm
brew install rpm
[default]
aws_access_key_id = <YOUR-DEV-ACCOUNT-ACCESS-KEY>
aws_secret_access_key = <YOUR-DEV-ACCOUNT-SECRET-KEY>
region = us-west-1
[profile lithiumdev]
aws_access_key_id = <YOUR-DEV-ACCOUNT-ACCESS-KEY>
aws_secret_access_key = <YOUR-DEV-ACCOUNT-SECRET-KEY>
# NOTE: Currently skybase client uses only "config" file to look for credentials. So, if you already have ~/.aws/credentials, then do
ln -s ~/.aws/config ~/.aws/credentials
It is in the backlog to remove the requirement for AWS creds from skybase client. So only Skybase creds will be needed.
2.2 Install Skybase Client
 
curl -L http://skybase.lcloud.com:8880/bootstrap-client | sudo bash -s -- lithium-prod

 
#
# NOTE: The command above will pause and wait for you to enter the password for sudo without displaying the prompt for it
#
# Enter the sudo password
#
 
2.3 Configuring Skybase Credentials.
Submit  JIRA ACCESS TICKET to get Skybase credentials and add them to your workstation
sky configure user-credentials -u <User_ID> -k <secret_key>
sky route ping -n 1
 
3. Sample workflows: Reference Service and ad hoc minimalistic Service
3.1 serviceX - basic "Hello, World!" service.
In this section we will A) get the code; B) Package service into artiball; C) deploy service; D) check it's status; E) delete service
git clone git@github.com:lithiumtech/skybase-reference.git
cd skybase-reference/serviceX

# Optional: if you installed fpm then you can rebuild the application
# or just for the reference you take a look of how to create an rpm for your Application
#  ./build.sh
 
 sky pack validate
 
# Create Skybase package and Save it's name into AB_NAME variable
 
export AB_NAME=`sky pack create -b DemoBuild`
Create will output the next command to upload and submit the artiball. 
# Upload artiball into Cloud folder
sky pack upload -a $AB_NAME

# Submit the artiball to the Skybase replicated Depot
sky pack submit -a $AB_NAME
Choose a Deploy_Tag . This will allow to create a unique name for the instantiation of the Service in the planet (e.g. Your-Initials-01 )
# make a useful alias for displaying json outputs
alias pj='python -m json.tool'
 
# NOTE: To make copy pasting of this tutorial more convenient, let's define a variable for DEPLOY_TAG :

export DEPLOY_TAG=<Deploy_Tag>

# Deploy your service to Dev planet in AWS region US-WEST-1 (NorCal)  
sky service deploy -a $AB_NAME -p dev-aws-us-west-1 -t $DEPLOY_TAG --apply | pj
 
# Deploy your service to Dev planet in Openstack in SJC1 datacenter (San Jose)
sky service deploy -a $AB_NAME -p dev-os-sjc1-1 -t $DEPLOY_TAG --apply | pj
sky service status -p dev-aws-us-west-1 -t $DEPLOY_TAG --verbose | pj
sky service status -p dev-os-sjc1-1 -t $DEPLOY_TAG --verbose | pj
 
sky service status -t $DEPLOY_TAG --verbose | pj
# "SKY SERIVE STATUS --VERBOSE" provides SKYBASE_ID for the stacks, which belong to a service
 
# you use the "skybase_id" to target a stack for deletion
sky service delete-stacks -p dev-aws-us-west-1 -s serviceX -t $DEPLOYTAG -k <Stack_Skybase_ID> --apply

# or you can use --delete-all-stacks option to delete all stackjs of a particular instantiation of the service:
sky service delete-stacks -p dev-aws-us-west-1 -s serviceX -t $DEPLOYTAG --delete-all-stacks --apply

# Delete One Stack from Openstack
sky service delete-stacks -p dev-os-sjc1-1 -s serviceX -t $DEPLOYTAG -k <Stack_Skybase_ID> --apply

# Or delete all stacks  
sky service delete -p dev-os-sjc1-1 -s serviceX -t $DEPLOYTAG --delete-all-stacks --apply
 
# Confirm that all stacks got deleted
sky service status -t $DEPLOYTAG | pj
 
3.2 Service1 - bare minimum service from scratch
The bare minimum information you need to have in order to launch a service is to provide a deployment template YAML file. 
NOTE: You can use a default directory if you change dir to the root of your service dir tree. 
mkdir service1
cd ./service1
sky pack init
vi skybase/skybase.yaml
packing:
  application:
    source_location:
  installations:
  - chef:
      repository_url: git@github.com:lithiumtech/skybase-reference.git
      repository_branch: master
      databags:
      encrypted_databags:
      cookbooks:
        dependencies_from_berkshelf: False
vi ./skybase/deployment/main_deployment.yaml
definition:
  service_name: service1
  version: 0.1.0
  keyname: skybase-demo
  chef_type: solo
  tags:
    TeamID: Skybase
    ServiceID: SkybaseDemo
    Email: skybot@lithium.com
stacks:
- name: MyFirstStack
  type: standard
  cloud_template_name: std-chef-solo/std-chef-solo
  roles:
  - name: MyFirstServer
    userdata_template_name: std-chef-solo/std-chef-solo
    type: disposable
    ami: ami-standard
    subnet: privateA
    instance_type: t1.micro
    root_volume_size: 8
    chef_role: MyFirstServer
    chef_role_runlist: []
    autoscaling: 1
    vpc_zone_identifier: private
    initial_capacity: 1
    max_capacity: 1
vi skybase/app_config/main_app_config.yaml
common:
stacks:
- name: MyFirstStack
  roles:
  - name: MyFirstServer
    universes:
      dev:
      qa:
      prod:
More about skybase packaging, deployment templates and app-config attributes configuration can be found in the "Skybase User Guide".
 
At this point you created a deployable service. Now let's validate, pack and deploy it.
# you should still be in the base dir of service  
sky pack validate
sky pack create -b DemoBuild 
# NOTE: The Output of the "SKY CREATE" command contains two lines with the next commands
 
# Upload artiball into Cloud folder
# COPY/PASTE the command from "sky create" output => sky pack upload -a <artiball_name>


# Submit the artiball to the Skybase replicated Depot
# COPY/PASTE the command from "sky create" output => sky pack submit -a <artiball_name>
# make a useful alias for displaying json outputs
alias pj='python -m json.tool'
 
# NOTE: To make copy pasting of this tutorial more convenient, let's define two environment variables:
export AB_NAME=<artiball_name>
export DEPLOY_TAG=<Deploy_Tag>
 
sky service deploy -a $AB_NAME -p dev-aws-us-west-1 -t $DEPLOY_TAG  --apply | pj
sky service deploy -a $AB_NAME -p dev-os-sjc1-1 -t $DEPLOY_TAG --apply | pj
Now you have deployed your service in both AWS and Openstack and you have 4 stacks running ( 2 in AWS and 2 in Openstack).
# Chech the status of the service deployment ACROSS ALL PLANETS
 
sky service status -t $DEPLOY_TAG --verbose | pj
Manually COPY RSA FILE FROM https://lithium.app.box.com/files/0/f/3095531947/Skybase TO YOUR LOACL DIR  ~/.ssh/
 
Manually COPY RSA FILE FROM https://lithium.app.box.com/files/0/f/3095531947/Skybase TO YOUR LOCAL DIR ~/.ssh/
 
 
# Now you can ssh to newly created servers in AWS and Openstack
ssh -i ~/.ssh/skybase-demo.rsa cloud-user@<ip_from_above_output>
ssh -i ~/.ssh/skybase-demo.rsa ec2-user@<ip_from_above_output>
sky service delete-stacks -p dev-aws-us-west-1 -s service1 -t $DEPLOY_TAG --delete-all-stacks --apply
sky service delete-stacks -p dev-os-sjc1-1 -s service1 -t $DEPLOY_TAG --delete-all-stacks --apply

# Verify that all instantiations of your service are removed from AWS and Openstack
sky service status -t $DEPLOY_TAG | pj
Support Diagrams
