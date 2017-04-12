CONTAINER_NAME=lpdm_db_container
NETWORK_NAME=lpdm_network
SUBNET=172.26.5.0/24
CONTAINER_IP=172.26.5.10
PG_PASS=12qwaszx
PG_PORT=5437

create_network:
	docker network create --subnet=${SUBNET} ${NETWORK_NAME}

remove_network:
	docker network rm ${NETWORK_NAME}

run:
	docker run --name ${CONTAINER_NAME} \
        -e POSTGRES_PASSWORD=${PG_PASS} \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        -v ${PWD}/docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d \
        -v ${PWD}/postgres_data:/var/lib/postgresql/data/pgdata \
        -p ${PG_PORT}:5432 \
        --net ${NETWORK_NAME} \
		--ip ${CONTAINER_IP} \
		-d postgres:9.6

stop:
	docker stop ${CONTAINER_NAME}

remove:
	docker rm ${CONTAINER_NAME}

clean:
	docker stop ${CONTAINER_NAME}
	docker rm ${CONTAINER_NAME}
	rm -rf postgres_data/

