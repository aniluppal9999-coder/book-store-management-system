# Bookstore Management System — Web Edition

A responsive browser-based bookstore manager based on the project report's features and visual references: navy left navigation, clean white/blue panels, catalogue forms, inventory tables, billing and sales history. This web implementation uses **Flask + MySQL** (instead of the report's Tkinter desktop UI) while retaining the same database-backed workflow.

## Included features

- Dashboard with catalogue count, copies in stock, today's revenue and low-stock count
- Add and edit books (title, author, ISBN, category, price, quantity)
- Search by title, author, ISBN or category
- Inventory view and quantity updates
- Sale cart: add/remove books and change quantities
- Billing subtotal, discount and optional tax calculation
- Stock validation and atomic MySQL transaction for sale + stock update; rollback if a sale fails
- Sales history and printable receipt
- Parameterised SQL queries and input validation

## Requirements

- Python 3.10+
- MySQL Server 8.x (running locally)
- A modern web browser

## Setup on Windows

1. Extract this folder.
2. Install Python packages from Command Prompt / PowerShell in this folder:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create the database and tables. Open MySQL Workbench or the MySQL command line, then run `schema.sql`.
4. Set database connection environment variables in the same terminal. Example for PowerShell (replace the password with your local MySQL password):

   ```powershell
   $env:DB_HOST="127.0.0.1"
   $env:DB_PORT="3306"
   $env:DB_USER="root"
   $env:DB_PASSWORD="your_mysql_password"
   $env:DB_NAME="bookstore_db"
   ```

   If your local MySQL root account has no password, set `$env:DB_PASSWORD=""`.
5. Start the application:

   ```powershell
   py app.py
   ```

6. Open **http://127.0.0.1:5000** in your browser.

The app also creates the required tables when it starts, provided the database itself already exists and the configured account has permission. `schema.sql` creates both the database and tables.

## Optional environment variables

- `SECRET_KEY`: set a private random value before deployment.
- `PORT`: web server port (default `5000`).
- `FLASK_DEBUG`: set to `1` only for local development. Do not enable debug mode on a public server.

## Important notes

- This is a local development project, not a hardened public deployment. Do not expose it to the internet without adding authentication, CSRF protection, production WSGI hosting, HTTPS and appropriate database permissions.
- Role-based login, barcode support, supplier management, multi-branch sync and online customer ordering were listed as optional/future enhancements in the report and are not implemented here.
- Receipts can be printed from the browser using the **Print receipt** button.
