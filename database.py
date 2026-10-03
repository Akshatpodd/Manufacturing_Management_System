"""Everything that talks to MySQL lives here.

Settings (optional): set the environment variables MYSQL_HOST, MYSQL_PORT,
MYSQL_USER and MYSQL_PASSWORD. Defaults: localhost, 3306, root, 1234.
"""
import os
from datetime import date
from tkinter import messagebox

import pymysql

DB_NAME = 'manufacturing_system'

# Name of the person who is logged in (filled by the login form, used in production reports)
current_user = {'name': 'Admin'}

# One CREATE TABLE statement per table (order matters: tables with links come last)
TABLES = [
    """CREATE TABLE IF NOT EXISTS employee_data (
        empid INT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        gender VARCHAR(50),
        contact VARCHAR(30),
        education VARCHAR(30),
        address VARCHAR(100),
        doj VARCHAR(30),
        salary VARCHAR(50),
        usertype VARCHAR(50),
        password VARCHAR(50))""",
    """CREATE TABLE IF NOT EXISTS supplier_data (
        invoice INT PRIMARY KEY,
        name VARCHAR(100),
        contact VARCHAR(15),
        description TEXT)""",
    # Raw materials we buy and keep in stock
    """CREATE TABLE IF NOT EXISTS material_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        unit VARCHAR(20) NOT NULL,
        quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
        reorder_level DECIMAL(12,3) NOT NULL DEFAULT 0,
        cost DECIMAL(10,2) NOT NULL DEFAULT 0,
        supplier VARCHAR(100))""",
    # Finished products we make
    """CREATE TABLE IF NOT EXISTS product_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        price DECIMAL(10,2) NOT NULL DEFAULT 0,
        quantity INT NOT NULL DEFAULT 0)""",
    # Recipe (bill of materials): how much of each material ONE unit of a product needs
    """CREATE TABLE IF NOT EXISTS bom_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        material_id INT NOT NULL,
        qty_per_unit DECIMAL(12,3) NOT NULL,
        UNIQUE KEY one_material_per_product (product_id, material_id),
        FOREIGN KEY (product_id) REFERENCES product_data(id) ON DELETE CASCADE,
        FOREIGN KEY (material_id) REFERENCES material_data(id) ON DELETE RESTRICT)""",
    # History of production runs
    """CREATE TABLE IF NOT EXISTS production_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT,
        product_name VARCHAR(100) NOT NULL,
        quantity INT NOT NULL,
        date_time DATETIME NOT NULL,
        produced_by VARCHAR(100),
        materials JSON NOT NULL)""",
]


def _server_settings():
    """Connection settings read from environment variables (with defaults)."""
    return dict(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '1234'),
        charset='utf8mb4',
    )


def initialize_database():
    """Create the database, all tables, and a first Admin login if no employee exists yet.

    Returns True when everything is ready, False if MySQL could not be reached.
    """
    try:
        connection = pymysql.connect(**_server_settings())
    except pymysql.MySQLError as exc:
        messagebox.showerror('Database Error', f'Could not connect to MySQL.\n\n{exc}')
        return False

    cursor = connection.cursor()
    try:
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME}')
        cursor.execute(f'USE {DB_NAME}')
        for create_table in TABLES:
            cursor.execute(create_table)

        # First run: nobody can log in yet, so create a default Admin (ID 1, password 1234)
        cursor.execute('SELECT COUNT(*) FROM employee_data')
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'INSERT INTO employee_data VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (1, 'Admin', 'admin@gmail.com', 'Male', '9876543210', 'B.Tech', 'Delhi',
                 date.today().strftime('%d/%m/%Y'), '0', 'Admin', '1234'))
        connection.commit()
        return True
    except pymysql.MySQLError as exc:
        messagebox.showerror('Database Error', f'Could not set up the database.\n\n{exc}')
        return False
    finally:
        cursor.close()
        connection.close()


def connect_database(retry=True):
    """Open a connection to the database. Returns (cursor, connection) or (None, None)."""
    try:
        connection = pymysql.connect(database=DB_NAME, autocommit=False, **_server_settings())
        return connection.cursor(), connection
    except pymysql.MySQLError as exc:
        # Error 1049 = the database does not exist yet: create it once and try again
        if retry and exc.args and exc.args[0] == 1049 and initialize_database():
            return connect_database(retry=False)
        messagebox.showerror('Database Error', f'Could not connect to MySQL.\n\n{exc}')
        return None, None


def run_query(sql, params=(), fetch=None, show_errors=True):
    """Run one SQL statement and close the connection afterwards.

    fetch='one'  -> returns the first row (or None if there is no row)
    fetch='all'  -> returns a list of rows
    fetch=None   -> for INSERT / UPDATE / DELETE: saves the change and returns True
    On an error it shows a message (unless show_errors=False) and returns None.
    """
    cursor, connection = connect_database()
    if not cursor or not connection:
        return None
    try:
        cursor.execute(sql, params)
        if fetch == 'one':
            return cursor.fetchone()
        if fetch == 'all':
            return cursor.fetchall()
        connection.commit()
        return True
    except pymysql.MySQLError as exc:
        connection.rollback()
        if show_errors:
            messagebox.showerror('Database Error', f'Error due to: {exc}')
        return None
    finally:
        cursor.close()
        connection.close()
