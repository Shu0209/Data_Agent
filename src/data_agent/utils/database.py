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



    def schema_details(self,schema_name):

        schema_info_context= ""

        connection=self.connection

        cursor=connection.cursor()

        schema_info_context=f"Database Schema: {schema_name}\n"
        try:
            cursor.execute("SELECT table_name from information_schema.tables where table_schema = %s;",(schema_name,))

            table_list=cursor.fetchall()

            for table in table_list:
                table_name=table[0]
                schema_info_context=f"{schema_info_context}\nTable: {table_name}\n"

                cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s;",(table_name,))

                columns_list=cursor.fetchall()

                for column in columns_list:
                    column_name=column[0]
                    data_type=column[1]
                    schema_info_context=f"{schema_info_context} Column: {column_name}, Data Type:{data_type}\n"


                # Adding Sample Data
                cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
                sample_data = cursor.fetchall()
                schema_info_context = f"{schema_info_context}  Sample Data:\n"
                for row in sample_data:
                    schema_info_context = f"{schema_info_context}    {row}\n"

        except Exception as e:
            print(f"Error fetching schema details: {e}")
            schema_info_context = f"Error fetching schema details: {e}"


        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        
        return schema_info_context

    def execute_sql(self, query):
        try:
            connection = self.connection
            cursor = connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            connection.commit()
            return str(result)
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


obj= DatabaseClass({
    "host":settings.DB_host,
    "port":settings.DB_port,
    "user":settings.DB_user,
    "password":settings.DB_password,
    "dbname":settings.DB_name
})


result=obj.schema_details("public")

with open("test_schema_details.txt","w") as f:
    f.write(result)




# import psycopg2
# from psycopg2 import sql
# from data_agent.config import settings


# class DatabaseClass:
#     def __init__(self, db_config):
#         self.db_config = db_config
#         self.connection = None

#         try:
#             self.connection = psycopg2.connect(**db_config)
#             print("Connected to PostgreSQL.")

#         except psycopg2.Error as e:
#             print(f"Error connecting to the database: {e}")

#     def schema_details(self, schema_name):
#         if self.connection is None:
#             return "Database connection is unavailable."

#         schema_info_context = f"Database Schema: {schema_name}\n"
#         cursor = None

#         try:
#             cursor = self.connection.cursor()

#             cursor.execute(
#                 """
#                 SELECT table_name
#                 FROM information_schema.tables
#                 WHERE table_schema = %s
#                   AND table_type = 'BASE TABLE'
#                 ORDER BY table_name;
#                 """,
#                 (schema_name,)
#             )

#             table_list = cursor.fetchall()

#             for (table_name,) in table_list:
#                 schema_info_context += f"\nTable: {table_name}\n"

#                 cursor.execute(
#                     """
#                     SELECT column_name, data_type
#                     FROM information_schema.columns
#                     WHERE table_schema = %s
#                       AND table_name = %s
#                     ORDER BY ordinal_position;
#                     """,
#                     (schema_name, table_name)
#                 )

#                 columns_list = cursor.fetchall()

#                 for column_name, data_type in columns_list:
#                     schema_info_context += (
#                         f"  Column: {column_name}, "
#                         f"Data Type: {data_type}\n"
#                     )

#                 sample_query = sql.SQL(
#                     "SELECT * FROM {}.{} LIMIT 5"
#                 ).format(
#                     sql.Identifier(schema_name),
#                     sql.Identifier(table_name)
#                 )

#                 cursor.execute(sample_query)
#                 sample_data = cursor.fetchall()

#                 schema_info_context += "  Sample Data:\n"

#                 for row in sample_data:
#                     schema_info_context += f"    {row}\n"

#         except psycopg2.Error as e:
#             print(f"Error fetching schema details: {e}")
#             schema_info_context = (
#                 f"Error fetching schema details: {e}"
#             )

#         finally:
#             if cursor is not None:
#                 cursor.close()

#             if self.connection is not None:
#                 self.connection.close()
#                 self.connection = None

#         return schema_info_context


# if __name__ == "__main__":
#     obj = DatabaseClass({
#         "host": settings.DB_host,
#         "port": settings.DB_port,
#         "user": settings.DB_user,
#         "password": settings.DB_password,
#         "dbname": settings.DB_name
#     })

#     result = obj.schema_details("public")

#     with open("test_schema_details.txt", "w", encoding="utf-8") as f:
#         f.write(result)

#     print("Schema details saved to test_schema_details.txt")
