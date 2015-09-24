# Skybase Installation and Configuration

There are several types of Skybase system installation:


1. Personal
2. Team scale (multi-user, single location)
3. Enterprise Scale (multi-user, multi-location )
4. Skybase Developer Installation
5. Demo (or "Try-it-Out") setup ????

The main difference between these types of installation is a location where different components of Skybase will be installed.

Note: For this initial release of the Skybase system into Open Source we did carve out the code from our internal CI/CD workflow.
At this time only the "Skybase Developer Installation" section is available.
And We are working on packaging for other types of install which will not be rely on Lithium internal processes.

## Personal Setup

Usage: Personal installation allows one person to use skybase to manage deployments into multiple clouds and control/manage 
different deployment supporting systems from a single location ( No authentication; all files and scripts are local ).

Installation:

"COMING SOON"

## Team Setup

Usage: Standalone Skybase server (All-In-One configuration) with multiple clients 

Installation:

"COMING SOON"

## Enterprise Setup

Usage: Central REST API Access point with Workers in multiple locations.

Installation:

"COMING SOON"

## Developer Setup

Usage: Skybase development itself. Run everything from local copy of the repository and use tools to make a development
process easier. A complete developer setup might include several VMs running together to provide a distributed topology

## Running from sources

Usage: Skybase is organized as a single python module and couple scripts to use this module. 
To run it from the source itself, you will need to set PYTHONPATH so the scripts can find the skybase module.

Installation:

### Get the code

### Install Prerequisites

### Place a minimum set of data in proper locations

### Setup the Runtime environment

### Add minimum set of credentials for the Cloud Provider(s) and supporting systems

( e.g. AWS and Hosted Chef)

### Launch all services locally and start development

1.
2. 
3. 


Enjoy!




