Run
Keep the assets/ folder next to the Python files.
Install the libraries: python -m pip install -r requirements.txt
Make sure MySQL is running.
MySQL settings default to host localhost, user root, password 1234. To change them, set MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD.
Start the app: python main.py
The database manufacturing_system and all tables are created automatically. First login (created automatically when there is no employee yet): Employee ID 1, Password 1234.

Suppliers: add the companies you buy from.
Materials: add each raw material with unit, stock, reorder level and cost. Use Receive Stock (+) when a delivery arrives. Rows turn red and say LOW when stock <= reorder level.
Products: add a finished product, select it, then build its recipe (how much of each material ONE unit needs).
Production: click + New Production, pick a product and quantity. The table shows needed vs available material. Start Production subtracts the materials and adds the finished units to the product stock. If any material is short, nothing is changed. Double-click a past run to see the materials it used.
Employee logins (user type Employee) open only the production order screen.


(must install)
PyMySQL>=1.1.0
tkcalendar>=1.6.1

