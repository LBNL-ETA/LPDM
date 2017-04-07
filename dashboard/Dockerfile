FROM node:7.8

# install python and libraries for running simulations
RUN apt-get update && apt-get install -y python2.7 python-pip python-dev

# install the simulation requirements
COPY requirements.txt /tmp/
RUN pip install --requirement /tmp/requirements.txt

# make the foldres for the backend, frontend, and simulation
RUN mkdir -p /frontend/src
RUN mkdir -p /backend/src
RUN mkdir -p /simulation/scenarios

# setup the front end npm packages
WORKDIR /frontend
COPY frontend/package.json /frontend/
RUN npm install

# setup the backend npm packages
WORKDIR /backend
COPY backend/package.json /backend/
RUN npm install

EXPOSE 3000
CMD ["npm", "start"]
