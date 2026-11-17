import os
import psycopg2
from psycopg2 import sql
from src.data_agent.config import settings



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_DIR = os.path.join(BASE_DIR, "data")

DB_CONFIG = {
    "host": settings.DB_host,
    "port": settings.DB_port,
    "database": settings.DB_name,
    "user": settings.DB_user,
    "password": settings.DB_password,
    "sslmode": settings.sslmode
}




# Tables configuration in topological loading order (parents first)
TABLE_CONFIG = [
    
    (
        "customers",
        "customers.csv",
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    ),
    (
        "sellers",
        "sellers.csv",
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    ),
    (
        "products",
        "products.csv",
        [
            "product_id",
            "product_category_name",
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    ),
    (
        "orders",
        "orders.csv",
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    ),
    (
        "order_items",
        "order_items.csv",
        [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    ),
    (
        "order_payments",
        "order_payments.csv",
        [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    ),
    (
        "order_reviews",
        "order_reviews.csv",
        [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    ),
]


def load_csv(cursor, table_name: str, csv_file: str, columns: list[str]):
    """Load a CSV file into a PostgreSQL table using copy_expert."""
    file_path = os.path.join(CSV_DIR, csv_file)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    copy_sql = sql.SQL("""
        COPY {} ({})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            QUOTE '"',
            ESCAPE '"',
            NULL ''
        )
    """).format(
        sql.Identifier("public", table_name),
        sql.SQL(", ").join(sql.Identifier(col) for col in columns),
    )

    # Use utf-8-sig to cleanly strip any UTF-8 BOM characters
    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        cursor.copy_expert(copy_sql.as_string(cursor.connection), file)

    print(f"Loaded {csv_file} -> public.{table_name}")


def main():
    conn = None

    try:
        print(f"Using CSV directory: {CSV_DIR}")
        print(f"Connecting to database at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        print("Connected to PostgreSQL successfully.")

        with conn.cursor() as cursor:
            # 1. Execute init.sql schema
            init_sql_path = os.path.join(BASE_DIR, "init.sql")
            print(f"Applying schema from {init_sql_path}...")
            with open(init_sql_path, "r", encoding="utf-8") as f:
                cursor.execute(f.read())
            print("Tables and indexes verified/created.")

            # 2. Truncate existing rows in child-first order
            cursor.execute("""
                TRUNCATE TABLE
                    public.order_reviews,
                    public.order_payments,
                    public.order_items,
                    public.orders,
                    public.products,
                    public.sellers,
                    public.customers
                CASCADE;
            """)
            print("Existing records cleared.")

            # 3. Load all tables in parent-first order
            print("\nStarting CSV data import...")
            for table_name, csv_file, columns in TABLE_CONFIG:
                load_csv(cursor, table_name, csv_file, columns)

            # 4. Display record counts
            print("\n" + "=" * 45)
            print("Record Counts in Database:")
            print("=" * 45)

            for table_name, _, _ in TABLE_CONFIG:
                cursor.execute(
                    sql.SQL("SELECT COUNT(*) FROM public.{}").format(
                        sql.Identifier(table_name)
                    )
                )
                count = cursor.fetchone()[0]
                print(f"{table_name:<30} {count:>12,}")

        # Commit all operations
        conn.commit()
        print("\nAll data loaded and committed successfully!")

    except (Exception, psycopg2.Error) as exc:
        if conn is not None:
            conn.rollback()
        print(f"\nDatabase loading failed: {exc}")
        print("Transaction rolled back.")
        raise

    finally:
        if conn is not None:
            conn.close()
            print("PostgreSQL connection closed.")


if __name__ == "__main__":
    main()
