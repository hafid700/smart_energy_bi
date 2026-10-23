
import pyodbc

SERVER = "LAPTOP-JG777V5I"
DATABASE = "DW_Smart_Energy"

connection_string = (
    "DRIVER={SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "Connection Timeout=5;"
)

try:
    print("Connexion à DW_Smart_Energy...")

    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                @@SERVERNAME,
                DB_NAME(),
                GETDATE()
        """)

        row = cursor.fetchone()

        print("Connexion réussie !")
        print("Serveur :", row[0])
        print("Base :", row[1])
        print("Date :", row[2])

except pyodbc.Error as e:
    print("Erreur :", e)
