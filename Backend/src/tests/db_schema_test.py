from data_agent.config import settings
from data_agent.utils.database import DatabaseClass


conn_details={
          "host":settings.DB_host,
          "port":settings.DB_port,
          "user":settings.DB_user,
          "password":settings.DB_password,
          "dbname":settings.DB_name  
     }

obj=DatabaseClass(conn_details)


schema_info = obj.schema_details("public")

print(schema_info)