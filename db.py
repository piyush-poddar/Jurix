import psycopg2
from dotenv import load_dotenv
import os
from typing import Optional

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

def get_db_connection():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )

def test_connection():
    try:
        connection = get_db_connection()
        print("Connection successful!")
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Current Time:", result)

        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")
    except Exception as e:
        print(f"Failed to connect: {e}")

def insert(
    table_name: str,
    content: str,
    embedding: list[float],
    title: str,
):
    """
    Inserts a new record into the table.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if table_name == "legal_docs":
            insert_query = f"""
            INSERT INTO {table_name} (content, embedding, title)
            VALUES (%s, %s, %s);
            """
        cursor.execute(insert_query, (content, embedding, title))

        connection.commit()
        print("Record inserted successfully.")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Failed to insert record: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def insert_many(
    table_name: str,
    records: list,
):
    """
    Inserts multiple records into the table.
    Each record is a tuple: (content, embedding, title)
    """
    connection = None
    cursor = None
    try:
        print(f"Preparing to insert {len(records)} records into {table_name}...")
        connection = get_db_connection()
        cursor = connection.cursor()
        if table_name == "legal_docs":
            insert_query = f"""
            INSERT INTO {table_name} (content, embedding, title)
            VALUES (%s, %s, %s);
            """
        elif table_name == "cases":
            insert_query = f"""
            INSERT INTO {table_name} (doc_id, case_title, section_type, content, embedding)
            VALUES (%s, %s, %s, %s, %s);
            """
        cursor.executemany(insert_query, records)
        connection.commit()
        print(f"{len(records)} records inserted successfully.")
    except Exception as e:
        print(f"Failed to insert records: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def fetch_similar_documents(
    table_name: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Fetches top_k similar documents based on cosine similarity.
    """
    connection = None
    cursor = None
    results = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if table_name == "legal_docs":
            fetch_query = f"""
            SELECT content, title,
            (1 - (embedding <=> %s::vector)) AS similarity
            FROM {table_name}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """
            cursor.execute(fetch_query, (query_embedding, query_embedding, top_k))
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    "content": row[0],
                    "title": row[1],
                    "similarity": row[2]
                })
        elif table_name == "cases":
            fetch_query = f"""
            SELECT content, case_title, section_type,
            (1 - (embedding <=> %s::vector)) AS similarity
            FROM {table_name}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """
            cursor.execute(fetch_query, (query_embedding, query_embedding, top_k))
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    "content": row[0],
                    "case_title": row[1],
                    "section_type": row[2],
                    "similarity": row[3]
                })
    except Exception as e:
        print(f"Failed to fetch documents: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return results

def check_if_docid_exists(
    doc_id: str,
) -> bool:
    """
    Checks if a document with the given doc_id exists in the cases table.
    """
    connection = None
    cursor = None
    exists = False
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        check_query = f"""
        SELECT EXISTS(
            SELECT 1 FROM cases WHERE doc_id = %s
        );
        """
        cursor.execute(check_query, (doc_id,))
        exists = cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to check document existence: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return exists

# if check_if_docid_exists("75521991"):
#     print("Document exists.")
# else:
#     print("Document does not exist.")