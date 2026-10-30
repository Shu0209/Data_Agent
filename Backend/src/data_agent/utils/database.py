# import re
# import time

# import psycopg2
# from psycopg2 import sql

# from data_agent.config import settings

# _SCHEMA_CACHE = {}          # schema_name -> (timestamp, text)
# SCHEMA_TTL_SECONDS = 600    # re-read the schema every 10 minutes
# _PII_COLUMN = re.compile(r"email|phone|name|address|plate|ssn|password|token|comment", re.I)


# class DatabaseClass:
#     def __init__(self, db_config):
#         self.db_config=db_config

#         try:
#             self.connection=psycopg2.connect(**db_config)

#         except Exception as e:
#             print(f"Error connection to the database: {e}")
#             self.connection=None


#     def schema_details(self, schema_name):
#         cached = _SCHEMA_CACHE.get(schema_name)
#         if cached and time.time() - cached[0] < SCHEMA_TTL_SECONDS:
#             if self.connection:
#                 self.connection.close()
#             return cached[1]

#         connection = self.connection
#         if connection is None:
#             return "Error fetching schema details: could not connect to the database"

#         cursor = connection.cursor()
#         try:
#             # 1 query for all columns, in table order
#             cursor.execute(
#                 "SELECT table_name, column_name, data_type "
#                 "FROM information_schema.columns WHERE table_schema = %s "
#                 "ORDER BY table_name, ordinal_position;", (schema_name,))
#             tables = {}
#             for t, c, d in cursor.fetchall():
#                 tables.setdefault(t, []).append((c, d))

#             # foreign keys, so the LLM knows how to JOIN
#             cursor.execute(
#                 "SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name "
#                 "FROM information_schema.table_constraints tc "
#                 "JOIN information_schema.key_column_usage kcu "
#                 "  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema "
#                 "JOIN information_schema.constraint_column_usage ccu "
#                 "  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema "
#                 "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s;",
#                 (schema_name,))
#             fks = {}
#             for t, col, ref_t, ref_c in cursor.fetchall():
#                 fks.setdefault(t, []).append(f"{col} -> {ref_t}.{ref_c}")

#             out = [f"Database Schema: {schema_name}\n"]
#             for table, columns in tables.items():
#                 out.append(f"\nTable: {table}\n")
#                 for col, dtype in columns:
#                     line = f" Column: {col}, Data Type:{dtype}"
#                     # list possible values for small categorical text columns
#                     if dtype in ("character varying", "text") and not _PII_COLUMN.search(col):
#                         cursor.execute(
#                             sql.SQL("SELECT DISTINCT {} FROM {}.{} WHERE {} IS NOT NULL LIMIT 11").format(
#                                 sql.Identifier(col), sql.Identifier(schema_name),
#                                 sql.Identifier(table), sql.Identifier(col)))
#                         values = [r[0] for r in cursor.fetchall()]
#                         if len(values) <= 10:
#                             line += f", Allowed values: {values}"
#                     out.append(line + "\n")
#                 for fk in fks.get(table, []):
#                     out.append(f" Foreign key: {fk}\n")

#             text = "".join(out)
#             _SCHEMA_CACHE[schema_name] = (time.time(), text)
#             return text

#         except Exception as e:
#             print(f"Error fetching schema details: {e}")
#             return f"Error fetching schema details: {e}"
#         finally:
#             cursor.close()
#             connection.close()

#     def execute_query(self, query):
#         connection = self.connection
#         cursor = None
#         try:
#             # read-only session: a write statement fails instead of being committed
#             connection.set_session(readonly=True)
#             cursor = connection.cursor()
#             cursor.execute(query)
#             result = cursor.fetchall()
#             return str(result)
#         except Exception as e:
#             print(f"Error executing query: {e}")
#             return None
#         finally:
#             if cursor:
#                 cursor.close()
#             if connection:
#                 connection.close()


# if __name__ == "__main__":
#     obj = DatabaseClass({
#         "host": settings.DB_host,
#         "port": settings.DB_port,
#         "user": settings.DB_user,
#         "password": settings.DB_password,
#         "dbname": settings.DB_name
#     })

#     result = obj.schema_details("public")

#     with open("test_schema_details.txt", "w") as f:
#         f.write(result)








import psycopg2
from data_agent.config import settings


class DatabaseClass:
    def __init__(self, db_config):
        self.db_config=db_config

        try:
            self.connection=psycopg2.connect(**db_config)

        except Exception as e:
            print(f"Error connection to the database: {e}")
            self.connection=None



    # def schema_details(self,schema_name):

    #     schema_info_context= ""

    #     connection=self.connection

    #     cursor=connection.cursor()

    #     schema_info_context=f"Database Schema: {schema_name}\n"
    #     try:
    #         cursor.execute("SELECT table_name from information_schema.tables where table_schema = %s;",(schema_name,))

    #         table_list=cursor.fetchall()

    #         for table in table_list:
    #             table_name=table[0]
    #             schema_info_context=f"{schema_info_context}\nTable: {table_name}\n"

    #             cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s;",(table_name,))

    #             columns_list=cursor.fetchall()

    #             for column in columns_list:
    #                 column_name=column[0]
    #                 data_type=column[1]
    #                 schema_info_context=f"{schema_info_context} Column: {column_name}, Data Type:{data_type}\n"


    #             # Adding Sample Data
    #             cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
    #             sample_data = cursor.fetchall()
    #             schema_info_context = f"{schema_info_context}  Sample Data:\n"
    #             for row in sample_data:
    #                 schema_info_context = f"{schema_info_context}    {row}\n"

    #     except Exception as e:
    #         print(f"Error fetching schema details: {e}")
    #         schema_info_context = f"Error fetching schema details: {e}"


    #     finally:
    #         if cursor:
    #             cursor.close()
    #         if connection:
    #             connection.close()
        
    #     return schema_info_context

    def execute_query(self, query):
        connection = self.connection
        cursor = None
        try:
            
            connection.set_session(readonly=True)
            cursor = connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            return str(result)
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


# if __name__ == "__main__":
#     obj = DatabaseClass({
#         "host": settings.DB_host,
#         "port": settings.DB_port,
#         "user": settings.DB_user,
#         "password": settings.DB_password,
#         "dbname": settings.DB_name
#     })

#     result = obj.schema_details("public")

#     with open("test_schema_details.txt", "w") as f:
#         f.write(result)





