#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER docker with encrypted password 'q^r+_#H=9fz&yGJ8';
    CREATE DATABASE lpdm;
    GRANT ALL PRIVILEGES ON DATABASE lpdm TO docker;
EOSQL
