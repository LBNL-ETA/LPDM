# script to start the lpdm dashboard

# make sure the docker_postgres folder is there
if [ -d docker_postgres ]
then
  # check if the container is already running
  if docker ps | grep lpdm_db_container
  then
    echo lpdm_db_container is running
  else
    # container is running, either start the stopped container, or run it
    echo "lpdm_db_container is not running... start"
    if docker ps -a | grep lpdm_db_container
    then
      # container is stopped
      docker start lpdm_db_container
    else
      cd docker_postgres
      make run
      cd ..
    fi
  fi

  # lpdm_db_container is running
  if docker ps | grep lpdm_sim_container
  then
    echo lpdm_sim_container is already running
  else
    if docker ps -a | grep lpdm_sim_container
    then
      docker start lpdm_sim_container
    else
      cd dashboard
      make run
    fi
  fi
fi
