# skybase.io

Skybase is a system to automate deployment and management of "services" in different "destinations". 
It "glues" multiple subsystems to create a simplified interface to control all of your infrastructure. 

Skybase installation scales from local all-in-one workstation to multi-user, multi-server and multi-region distributed
systems. You can think of Skybase as "A Deployment Tool, which grows with you and your company".

Skybase is "The Thing", which executes for you three commands "deploy service", "modify service" and "delete service".

In order to deploy a service Skybase performs 3 actions: 
1) prepare supporting services; 
1) provision compute resources;
1) initialize service on newly provisioned resources.

Modification/Management of resources from Skybase perspective:
1) find resources
1) update support services
1) trigger the change action on the service resources

Delete service means:
1) find resources
1) delete resources
1) cleanup supporting services



## Installation

All three types of skybase installation: personal, team edition and for skybase development are described [HERE](docs/Installation.md)

## 