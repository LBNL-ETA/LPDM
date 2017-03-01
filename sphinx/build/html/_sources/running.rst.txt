Running Simulations
===================

Setting up the Docker Environment
---------------------------------
The Dockerfile in the root of the LPDM repository will setup the image for running
simulations.  The Makefile in the root of the LPDM repository provides the docker commands
needed to run a simulation.

Creating the Docker Network
___________________________
Prior to running any simulations, first run the following command from the root directory of the LPDM repository::

    make create network

This will run the ``docker network create`` command to setup the network for the docker containers.
Since the optional PostgreSQL database (used for logging) is run inside a separate docker container, creating
a custom network with static IP addresses will faciliate communication between the two containers.

Starting the PostgreSQL Database
________________________________
The docker_postgres folder contains a Makefile, which has the Docker commands needed to
start the database container, some scripts needed for the Postgres image, and a folder named **postgres_data**,
which is setup as a shared volume with the container in order to persist the database when the
container is finished running.

From inside the docker_postgres folder run::

    make run

This will start the PostgreSQL docker container as a daemon process.

Logging to PostgreSQL
_____________________
To enable logging to PostgreSQL first start the database container with the steps outlined above.

The LPDM repository containers a folder named **simulation_logger** which contains the code for
setting up the various logging mechanisims: 1) console, 2) file, and 3) database.  To enabled the
database logging feature see the pg.cfg file and set the **enabled** property to 1.  If the
Makefile is used to start the containers, the other properties should not need to be changed.

.. note::

    There is currently not an interface set up to view the PostgreSQL log output, so the only
    way to look at it is with a PostgreSQL client.  The Makefile command for starting the PostgreSQL
    container will map the container's database port (5432) to port (5437) on your local machine.

Running Simulations
___________________
Before running any simulations the docker image must first be built::

    make build_image

This will run the ``docker build`` command to create the image outlined in the Dockerfile.

Once the image is built, run::

    make run

This will run the ``docker run`` command and execute the default command specified in the Dockerfile.
Once the simulation has finished running the container should automatically exit.

The log files for the simulations can be found in the **logs** folder.
