IMG_NAME=lpdm_sim_img
CONTAINER_NAME=lpdm_sim_container
NETWORK_NAME=lpdm_network
SUBNET=172.26.5.0/24
CONTAINER_IP=172.26.5.5

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
	-v ${CURDIR}:/LPDM \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	${IMG_NAME} /bin/bash

run:
	docker run -it --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}:/LPDM \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	${IMG_NAME}

run_scenario:
	echo "run scenario file: ${SCENARIO_FILE}"
	docker run -it --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}:/LPDM \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	${IMG_NAME} \
	python run_scenarios.py ${SCENARIO_FILE}

test:
	docker run -it --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}:/LPDM \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	${IMG_NAME} \
	python -m unittest discover

test_file:
	echo "run test file: ${TEST_FILE}"
	docker run -it --rm --name=${CONTAINER_NAME} \
	-v ${CURDIR}:/LPDM \
	--net=${NETWORK_NAME} \
	--ip ${CONTAINER_IP} \
	-e "PYTHONPATH=/LPDM" \
	${IMG_NAME} \
	python ${TEST_FILE}

