import mysql.connector
from mysql.connector import Error
try:
    connection = mysql.connector.connect(host='35.221.12.48',
                             database='db',
                             user='root',
                             password='L05nE0na1pl2Dei3')
    if connection.is_connected():
       db_Info = connection.get_server_info()
       print("Connected to MySQL database")
       cursor = connection.cursor()

       sql_insert_query = "INSERT INTO courses (id) VALUES (1)"
       cursor.execute(sql_insert_query)
       connection.commit()

except Error as e :
    print ("Error while connecting to MySQL", e)
    connection.rollback()
    exit(1)
finally:
    #closing database connection.
    if(connection.is_connected()):
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
