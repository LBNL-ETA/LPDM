import os
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
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()

            # if self.config.get("clean", False):
            # self.remove_tables("public")
            if not self.schema_has_tables(self.schema):
                self.build_tables("public")
            # if self.config.has_key("pg_schema") and self.config["pg_schema"] and self.config["pg_schema"] != "public":
                # self.set_schema(self.config["pg_schema"])
            self.set_run_id()

    def schema_has_tables(self, schema_name):
        """Check if a schema has the required tables for the simulation"""
        try:
            self.cursor.execute("select * from {}.sim_log limit 1".format(schema_name))
            self.cursor.execute("select * from {}.sim_device limit 1".format(schema_name))
            self.cursor.execute("select * from {}.sim_run limit 1".format(schema_name))
            return True
        except:
            return False

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
        self.build_tables(self, schema_name)

    def build_tables(self, schema_name="public"):
        """Build the tables needed for the simuluations for a specified schema name"""
        query = """
            create table public.sim_run (
                id serial primary key,
                time_stamp timestamp default now(),
                connection_id text,
                config json
            )
        """.format(schema_name)
        self.cursor.execute(query)

        # try:
            # self.cursor.execute("""
                # create table {}.sim_run (
                    # id serial primary key,
                    # time_stamp timestamp default now(),
                    # connection_id text,
                    # config json
                # )
            # """.format(schema_name))
        # except psycopg2.Error as e:
            # print "psycopg2 error: {} - {}".format(e.pgcode, e.pgerror)

        self.cursor.execute("""
            create table public.sim_device (
                id serial primary key,
                run_id int references public.sim_run (id) not null,
                device_class varchar(20) not null,
                device_id varchar(20) not null,
                unique (run_id, device_id)
            )
        """.format(schema_name))
        self.cursor.execute("""
            create table public.sim_log (
                id serial primary key,
                run_id int references public.sim_run (id) not null,
                sim_device_id int references sim_device (id),
                device varchar(20),
                message varchar(200),
                tag varchar(20),
                value float8,
                time_value float8,
                time_string text
            )
        """.format(schema_name))

    def remove_tables(self, schema_name="public"):
        """Remove all the simulation tables from the db"""
        queries = []
        queries.append("drop table {}.sim_log".format(schema_name))
        queries.append("drop table {}.sim_device".format(schema_name))
        queries.append("drop table {}.sim_run".format(schema_name))
        for query in queries:
            try:
                self.cursor.execute(query)
            except:
                pass
        self.conn.commit()

    def set_run_id(self):
        """
        Setup the simulation in the database.
        Insert a new record into the sim_run table and get the id field.
        """
        connection_id = os.environ.get("CONNECTION_ID", None)
        self.cursor.execute(
            "insert into {}.sim_run (time_stamp, connection_id) values (now(), %s) returning id".format(self.schema),
            [connection_id]
        )
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
            if len(db_fields["message"]) >= 200:
                db_fields["message"] = db_fields["message"][:199]
            params.extend([db_fields[key] if db_fields[key] != 'None' else None for key in db_fields.keys()])
            self.cursor.execute(query, params)
            self.conn.commit()

    def parse_message(self, message):
        """parse a log message into parts"""
        parts = message.split(";")
        if len(parts) == 6:
            parts = [p.strip() for p in parts]
            return {
                "time_string": parts[0] if parts[0] != "" else None,
                "time_value": parts[1] if parts[1] != "" else None,
                "device": parts[2] if parts[2] != "" else None,
                "tag": parts[3] if parts[3] != "" else None,
                "value": parts[4] if parts[4] != "" else None,
                "message": parts[5]
            }
        else:
            return {"message": message}
