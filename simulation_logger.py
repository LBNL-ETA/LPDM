

################################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v1.0"
# Copyright (c) 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
################################################################################################################################

import os
import re
import logging
import coloredlogs
import psycopg2

class PgHandler(logging.Handler):
    """
    Create a new logging handler for writing to PostgreSQL
    """
    def __init__(self, config):
        logging.Handler.__init__(self)
        self.conn = None
        self.cursor = None
        self.schema = "public"
        self.config = config if type(config) is dict else None

        self.sim_run_id = None
        self.device_id_map = {}

    def connect(self):
        """create a connection to the database"""
        if type(self.config) is dict and self.config.get("pg_enabled", None):
            self.conn = psycopg2.connect(
                    host=self.config["pg_host"],
                    port=self.config["pg_port"],
                    dbname=self.config["pg_dbname"],
                    user=self.config["pg_user"],
                    password=self.config["pg_pass"]
                )
            self.cursor = self.conn.cursor()

            if self.config.has_key("pg_schema") and self.config["pg_schema"] and self.config["pg_schema"] != "public":
                self.set_schema(self.config["pg_schema"])
        self.set_run_id()

    def set_schema(self, schema_name):
        """set the schema to write the logs to. Create it if it doesn't exist"""
        if not self.schema_exists(schema_name):
            self.create_schema(schema_name)
        self.schema = schema_name

    def schema_exists(self, schema_name):
        """test if a schema exists"""
        self.cursor.execute(
            "select exists(select schema_name from information_schema.schemata where schema_name = %s)",
            [schema_name]
        )
        row = self.cursor.fetchone()
        return row[0]

    def create_schema(self, schema_name):
        """create a schema and all of the tables for the simulation"""
        self.cursor.execute("create schema {}".format(schema_name))
        self.cursor.execute("""
            create table {}.sim_run (
                id serial primary key,
                time_stamp timestamp default now(),
                config json
            )
        """.format(schema_name))
        self.cursor.execute("""
            create table {0}.sim_device (
                id serial primary key,
                run_id int references {0}.sim_run (id) not null,
                device_class varchar(20) not null,
                device_id varchar(20) not null,
                unique (run_id, device_id)
            )
        """.format(schema_name))
        self.cursor.execute("""
            create table {0}.sim_log (
                id serial primary key,
                run_id int references {0}.sim_run (id) not null,
                sim_device_id int references sim_device (id),
                device varchar(20),
                message varchar(200),
                tag varchar(20),
                value float8,
                time_value float8
            )
        """.format(schema_name))
        self.conn.commit()

    def set_run_id(self):
        """
        Setup the simulation in the database.
        Insert a new record into the sim_run table and get the id field.
        """
        self.cursor.execute("insert into {}.sim_run (time_stamp) values (now()) returning id".format(self.schema))
        row = self.cursor.fetchone()
        self.sim_run_id = row[0]
        print "run id = {}".format(self.sim_run_id)
        self.conn.commit()

    def emit(self, record):
        print "Emit record to db...."
        print record.msg
        db_fields = self.parse_message(record.msg)
        print db_fields
        if len(db_fields.keys()):
            names = ["run_id"]
            names.extend(db_fields.keys())

            query = """
                insert into {0}.sim_log ({1}) values ({2})
            """.format(self.schema, ", ".join(names), ", ".join(['%s' for n in names]))
            print query
            print db_fields.keys()
            params = [self.sim_run_id]
            params.extend([db_fields[key] if db_fields[key] != 'None' else None for key in db_fields.keys()])
            print params
            self.cursor.execute(query, params)
            self.conn.commit()

    def parse_message(self, message):
        """parse a log message into parts"""
        print message
        fields = ["message", "tag", "value", "device", "time_value"]
        field_map = {}
        for field in fields:
            results = re.search(r"\b" + field + r": (.*?)($|, \w+:)", str(message), re.I)
            if results:
                field_map[field] = results.groups()[0]
        return field_map

class SimulationLogger:
    """
    This class sets up the logging and handlers for the simulation.
    """

    def __init__(self, verbose=True):
        self.app_name = "lpdm"
        self.base_path = "logs"
        self.folder = None
        self.log_id = None
        self.logger = None
        self.verbose = verbose

    def initializeLogging(self):
        """Setup the log paths and create the logging handlers"""
        self.generateSimulationId()
        self.createSimulationLogFolder()
        self.createSimulationLogger()

    def generateSimulationId(self):
        """build a unique id for each simulation"""
        max_id = 0
        for dirname in os.listdir(self.base_path):
            if re.match(r'^simulation_(\d+)$', dirname):
                parts = dirname.split("_")
                current_id = int(parts[1])
                if current_id > max_id:
                    max_id = current_id

        self.log_id = max_id + 1

    def simulationLogPath(self):
        if self.log_id is None:
            raise Exception("Simulation id has not been set.")
        else:
            return os.path.join(self.base_path, "simulation_{}".format(self.log_id))

    def createSimulationLogFolder(self):
        os.mkdir(self.simulationLogPath())

    def appName(self):
        return "{}_{}".format(self.app_name, self.log_id)

    def createSimulationLogger(self):
        """
        Create the loggers and handlers for the app.
        Create an app level logger that stores log messages for the entire app.
        Next create a console handler to print output to the console.
        Create handler for writing log messages to Postgres
        """
        self.logger = logging.getLogger(self.appName())
        self.logger.setLevel(logging.DEBUG)
        # coloredlogs.install(level='INFO', logger=logger)

        # create file handler which logs even debug messages
        fh = logging.FileHandler(os.path.join(self.simulationLogPath(), 'app.log'), mode='w')
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        colored_formatter = coloredlogs.ColoredFormatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        ch.setFormatter(colored_formatter)
        fh.setFormatter(formatter)

        # setup the database logger
        config = {
            "pg_enabled": True,
            "pg_host": "172.22.0.2",
            "pg_port": "5432",
            "pg_dbname": "lpdm",
            "pg_user": "docker",
            "pg_pass": "q^r+_#H=9fz&yGJ8",
            "pg_schema": "mikey2"
        }
        db_handler = PgHandler(config)
        db_handler.connect()
        db_handler.setLevel(logging.DEBUG)

        # add the handlers to logger
        if self.verbose:
            self.logger.addHandler(ch)
        self.logger.addHandler(fh)
        self.logger.addHandler(db_handler)

