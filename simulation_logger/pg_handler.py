import re
import logging
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
        if type(self.config) is dict:
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
                time_value float8,
                time_string text
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
        self.conn.commit()

    def emit(self, record):
        db_fields = self.parse_message(record.msg)
        if len(db_fields.keys()):
            names = ["run_id"]
            names.extend(db_fields.keys())

            query = """
                insert into {0}.sim_log ({1}) values ({2})
            """.format(self.schema, ", ".join(names), ", ".join(['%s' for n in names]))
            params = [self.sim_run_id]
            params.extend([db_fields[key] if db_fields[key] != 'None' else None for key in db_fields.keys()])
            self.cursor.execute(query, params)
            self.conn.commit()

    def parse_message(self, message):
        """parse a log message into parts"""
        fields = ["message", "tag", "value", "device", "time_value", "time_string"]
        field_map = {}
        for field in fields:
            results = re.search(r"\b" + field + r": (.*?)($|, \w+:)", str(message), re.I)
            if results:
                field_map[field] = results.groups()[0]
        return field_map

