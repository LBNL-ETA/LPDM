IMG_NAME=lpdm_dash_img
CONTAINER_NAME=lpdm_dash_container
NETWORK_NAME=lpdm_network
SUBNET=172.26.5.0/24
CONTAINER_IP=172.26.5.12

create_network:
	docker network create --subnet=${SUBNET} ${NETWORK_NAME}

remove_network:
	docker network rm ${NETWORK_NAME}

build_image:
	docker build -t=${IMG_NAME} --rm=true .

build_image_no_cache:
	docker build -t=${IMG_NAME} --rm=true --no-cache .

remove_image:
	docker rmi ${IMG_NAME}

start_container_bash:
	docker run -ti --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}/frontend/src:/frontend/src \
	-v ${CURDIR}/backend/src:/backend/src \
	-v ${CURDIR}/../simulation:/simulation \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	-p 3000:3000 \
	${IMG_NAME} /bin/bash

run:
	docker run -it --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}/frontend/src:/frontend/src \
	-v ${CURDIR}/backend/src:/backend/src \
	-v ${CURDIR}/../simulation:/simulation \
	-p 3000:3000 \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	${IMG_NAME}
