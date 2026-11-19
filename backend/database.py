import os

import psycopg
from psycopg.rows import dict_row


def get_connection():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=10,
        row_factory=dict_row,
    )


def check_database():
    with get_connection() as connection:
        result = connection.execute(
            """
            SELECT
                current_database() AS database,
                (
                    SELECT COUNT(*)
                    FROM inovidus_demo.rental_contracts
                ) AS contracts,
                (
                    SELECT COUNT(*)
                    FROM inovidus_demo.maintenance_cases
                ) AS maintenance_cases
            """
        ).fetchone()

    return result


if __name__ == "__main__":
    result = check_database()

    print("Database connection successful.")
    print(f"Database: {result['database']}")
    print(f"Contracts: {result['contracts']}")
    print(f"Maintenance cases: {result['maintenance_cases']}")