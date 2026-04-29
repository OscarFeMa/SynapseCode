import sqlite3
import os

db_path = r"d:\proyectos\Synapse\data\synapse.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column, type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type}")
        print(f"Added {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding {column} to {table}: {e}")

# SequentialDebate
add_column("sequential_debates", "structured_report", "JSON")

# AgentCall
add_column("agent_calls", "quality_score", "FLOAT")
add_column("agent_calls", "intervention_type", "VARCHAR(50)")

conn.commit()
conn.close()
print("Migration completed.")
