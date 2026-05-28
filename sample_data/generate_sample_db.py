import os
import sqlite3

def generate_sample_database(db_path: str):
    """Creates a sample SQLite database representing a basic eCommerce model."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove existing db file if any to start clean
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        signup_date DATE DEFAULT CURRENT_DATE
    );
    """)

    cursor.execute("""
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER DEFAULT 0
    );
    """)

    cursor.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        price_at_purchase REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    # Seed data
    cursor.execute("INSERT INTO users (name, email) VALUES ('Alice Smith', 'alice@example.com')")
    cursor.execute("INSERT INTO users (name, email) VALUES ('Bob Jones', 'bob@example.com')")

    cursor.execute("INSERT INTO products (title, price, stock_quantity) VALUES ('Laptop', 999.99, 10)")
    cursor.execute("INSERT INTO products (title, price, stock_quantity) VALUES ('Mouse', 25.50, 100)")
    cursor.execute("INSERT INTO products (title, price, stock_quantity) VALUES ('Keyboard', 75.00, 50)")

    cursor.execute("INSERT INTO orders (user_id, status) VALUES (1, 'completed')")
    cursor.execute("INSERT INTO orders (user_id, status) VALUES (2, 'pending')")

    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (1, 1, 1, 999.99)")
    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (1, 2, 2, 25.50)")
    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (2, 3, 1, 75.00)")

    conn.commit()
    conn.close()
    print(f"Sample database created successfully at: {db_path}")

if __name__ == "__main__":
    generate_sample_database("sample_data/ecommerce.db")
