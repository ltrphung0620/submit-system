from __future__ import annotations

import os

import pyodbc

SERVER = os.environ.get("SQLSERVER_HOST", "ltrphung")
DATABASE = "submission"


def main() -> None:
    connection = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};DATABASE=master;"
        "Trusted_Connection=yes;TrustServerCertificate=yes;",
        autocommit=True,
        timeout=5,
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            "IF DB_ID(?) IS NULL EXEC('CREATE DATABASE [' + ? + ']')",
            DATABASE,
            DATABASE,
        )
        print(f"SQL Server database '{DATABASE}' is ready on '{SERVER}'.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
