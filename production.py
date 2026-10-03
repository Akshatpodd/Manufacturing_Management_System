import json
import time
from datetime import datetime, timedelta
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

from database import connect_database, run_query, current_user
from ui import (setup_theme, center_window, make_label, make_entry, make_text, make_button, make_radio,
                create_treeview, fill_treeview, fmt_number, BLUE)

FILTER_DAYS = {'weekly': 7, 'monthly': 30}


# ------------------------------------------------------------ production logic
def load_products():
    """Return {product name: product id} for the dropdown."""
    rows = run_query('SELECT id, name FROM product_data ORDER BY name', fetch='all') or []
    return {name: product_id for product_id, name in rows}


def get_requirements(product_id, quantity):
    """Materials needed to make `quantity` units: list of (name, unit, needed, available, enough)."""
    rows = run_query('SELECT m.name, m.unit, b.qty_per_unit, m.quantity FROM bom_data b '
                     'JOIN material_data m ON m.id = b.material_id WHERE b.product_id=%s ORDER BY m.name',
                     (product_id,), fetch='all') or []
    return [(name, unit, per_unit * quantity, available, available >= per_unit * quantity)
            for name, unit, per_unit, available in rows]


def run_production(product_id, product_name, quantity):
    """Use up the materials and add the finished units in ONE transaction (all or nothing).

    Returns the report text, or None if the production could not be done.
    """
    cursor, connection = connect_database()
    if not cursor or not connection:
        return None
    try:
        # FOR UPDATE locks the rows so two people cannot use the same material at the same time
        cursor.execute('SELECT m.id, m.name, m.unit, b.qty_per_unit, m.quantity FROM bom_data b '
                       'JOIN material_data m ON m.id = b.material_id WHERE b.product_id=%s '
                       'ORDER BY m.name FOR UPDATE', (product_id,))
        recipe = cursor.fetchall()
        if not recipe:
            raise ValueError('This product has no recipe yet.\nAdd its materials in the Products screen first.')

        used, shortages = [], []
        for material_id, name, unit, per_unit, available in recipe:
            needed = per_unit * quantity
            if available < needed:
                shortages.append(f'{name}: need {fmt_number(needed)} {unit}, have {fmt_number(available)}')
            used.append((material_id, name, unit, needed))
        if shortages:
            raise ValueError('Not enough material:\n\n' + '\n'.join(shortages))

        for material_id, _name, _unit, needed in used:
            cursor.execute('UPDATE material_data SET quantity = quantity - %s WHERE id=%s', (needed, material_id))
        cursor.execute('UPDATE product_data SET quantity = quantity + %s WHERE id=%s', (quantity, product_id))
        cursor.execute('SELECT quantity FROM product_data WHERE id=%s', (product_id,))
        new_stock = cursor.fetchone()[0]

        date_time = time.strftime('%Y-%m-%d %H:%M:%S')
        materials = [{'material': name, 'quantity': float(needed), 'unit': unit} for _id, name, unit, needed in used]
        cursor.execute('INSERT INTO production_data (product_id, product_name, quantity, date_time, produced_by, '
                       'materials) VALUES (%s, %s, %s, %s, %s, %s)',
                       (product_id, product_name, quantity, date_time, current_user['name'], json.dumps(materials)))
        connection.commit()
    except ValueError as e:
        connection.rollback()
        messagebox.showerror('Cannot start production', str(e))
        return None
    except Exception as e:
        connection.rollback()
        messagebox.showerror('Database Error', f'Could not save the production run: {e}')
        return None
    finally:
        cursor.close()
        connection.close()

    lines = ['*** Production Report ***', '', f'Product: {product_name}', f'Units made: {quantity}',
             f'Date & Time: {date_time}', f"Produced by: {current_user['name']}", '', 'Materials used:']
    for item in materials:
        lines.append(f"  {item['material'][:22]:<24}{fmt_number(item['quantity']):>10} {item['unit']}")
    lines += ['', f'Stock of {product_name} is now: {new_stock}']
    return '\n'.join(lines)


# ------------------------------------------------------------ the production order panels
def build_production_panels(container, on_saved=None):
    """Create the 'Production Order' panel and the report panel inside `container`."""
    container.grid_rowconfigure(0, weight=1)
    container.grid_columnconfigure(0, weight=3, minsize=560)
    container.grid_columnconfigure(1, weight=2, minsize=380)
    products = load_products()

    # ---- left: order form + material check ----
    left = Frame(container, bg='white', bd=3, relief=RIDGE)
    left.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
    make_label(left, 'Production Order', font=('Helvetica', 16, 'bold'), bg=BLUE, fg='white').pack(fill='x')

    form = Frame(left, bg='white')
    form.pack(pady=12)
    make_label(form, 'Product', ('Helvetica', 13, 'bold')).grid(row=0, column=0, padx=10, pady=8, sticky='w')
    product_combobox = ttk.Combobox(form, values=list(products), font=('Helvetica', 13), width=22, state='readonly')
    product_combobox.set('Select product')
    product_combobox.grid(row=0, column=1, padx=10)
    make_label(form, 'Quantity to make', ('Helvetica', 13, 'bold')).grid(row=1, column=0, padx=10, pady=8, sticky='w')
    quantity_entry = make_entry(form, ('Helvetica', 13), width=12)
    quantity_entry.grid(row=1, column=1, padx=10, sticky='w')

    make_label(left, 'Materials needed for this order', ('Helvetica', 12, 'bold')).pack(anchor='w', padx=14)
    table_frame = Frame(left, bg='white')
    table_frame.pack(fill=BOTH, expand=1, padx=10, pady=4)
    requirement_tree = create_treeview(
        table_frame, ('material', 'needed', 'available', 'status'),
        ('Material', 'Needed', 'Available', 'Status'), (200, 100, 100, 90),
        anchors=('w', 'e', 'e', 'center'))
    requirement_tree.tag_configure('short', foreground='#b91c1c')
    requirement_tree.tag_configure('ok', foreground='#15803d')
    status_label = make_label(left, '', ('Helvetica', 12, 'bold'))
    status_label.pack(pady=4)

    # ---- right: report ----
    right = Frame(container, bg='white', bd=3, relief=RIDGE)
    right.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
    right.grid_rowconfigure(1, weight=1)
    right.grid_columnconfigure(0, weight=1)
    make_label(right, 'Production Report', font=('Helvetica', 16, 'bold'), bg=BLUE, fg='white'
               ).grid(row=0, column=0, sticky='we')
    report_text = make_text(right, width=10, height=10, font=('Courier', 11), bg='white')
    report_text.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
    report_text.config(state=DISABLED)

    def read_order():
        """Return (product_id, name, quantity) or None (quiet: used while typing)."""
        name = product_combobox.get()
        text = quantity_entry.get().strip()
        if name not in products or not text.isdigit() or not 0 < int(text) <= 1000000:
            return None
        return products[name], name, int(text)

    def check_materials(event=None):
        """Show what the order needs and whether the stock is enough."""
        requirement_tree.delete(*requirement_tree.get_children())
        order = read_order()
        if order is None:
            status_label.config(text='')
            return
        requirements = get_requirements(order[0], order[2])
        if not requirements:
            status_label.config(text='No recipe for this product yet', fg='#b91c1c')
            return
        for name, unit, needed, available, enough in requirements:
            requirement_tree.insert('', END, tags=('ok' if enough else 'short',), values=(
                f'{name} ({unit})', fmt_number(needed), fmt_number(available), 'OK' if enough else 'SHORT'))
        if all(item[4] for item in requirements):
            status_label.config(text='Enough material: ready to produce', fg='#15803d')
        else:
            status_label.config(text='Not enough material for this quantity', fg='#b91c1c')

    def start_production():
        order = read_order()
        if order is None:
            messagebox.showerror('Error', 'Select a product and enter a whole number quantity (1 or more).')
            return
        report = run_production(*order)
        if report is None:
            check_materials()
            return
        report_text.config(state=NORMAL)
        report_text.delete('1.0', END)
        report_text.insert(END, report)
        report_text.config(state=DISABLED)
        quantity_entry.delete(0, END)
        check_materials()
        if on_saved:
            on_saved()
        messagebox.showinfo('Success', 'Production saved. Materials used and stock updated.')

    make_button(left, 'Start Production', font=('Helvetica', 14, 'bold'), bg='#15803d',
                command=start_production).pack(pady=(0, 12))
    product_combobox.bind('<<ComboboxSelected>>', check_materials)
    quantity_entry.bind('<KeyRelease>', check_materials)


def open_new_production_window(parent, on_saved=None):
    """Open the production order in its own window (used by Admin: Production > New Production)."""
    order_window = Toplevel(parent)
    order_window.title('New Production')
    order_window.config(bg='white')
    center_window(order_window, 1100, 560)
    order_window.transient(parent)
    make_label(order_window, 'New Production Run', font=('Helvetica', 18, 'bold'), bg=BLUE, fg='white'
               ).pack(fill='x')
    container = Frame(order_window, bg='white')
    container.pack(fill=BOTH, expand=1)
    build_production_panels(container, on_saved)


# ------------------------------------------------------------ history (Admin screen)
def calculate_totals():
    """Return (units made in the last 7 days, units made in the last 30 days)."""
    totals = []
    for days in (FILTER_DAYS['weekly'], FILTER_DAYS['monthly']):
        row = run_query('SELECT COALESCE(SUM(quantity), 0) FROM production_data WHERE date_time >= %s',
                        (datetime.now() - timedelta(days=days),), fetch='one')
        totals.append(int(row[0]) if row else 0)
    return totals[0], totals[1]


def fetch_runs(filter_type='all'):
    """Production runs of the chosen filter, newest first."""
    sql = 'SELECT id, product_name, quantity, date_time, produced_by FROM production_data'
    params = ()
    if filter_type in FILTER_DAYS:
        sql += ' WHERE date_time >= %s'
        params = (datetime.now() - timedelta(days=FILTER_DAYS[filter_type]),)
    return run_query(sql + ' ORDER BY date_time DESC', params, fetch='all') or []


def update_history(treeview, filter_type):
    """Show the production runs of the chosen filter in the table."""
    fill_treeview(treeview, [(run_id, name, quantity, date_time.strftime('%Y-%m-%d %H:%M:%S'), by or '')
                             for run_id, name, quantity, date_time, by in fetch_runs(filter_type)])


def open_run_details(event, treeview):
    """Double-click a run to see which materials it used."""
    selection = treeview.selection()
    if not selection:
        return
    run_id = treeview.item(selection[0])['values'][0]
    row = run_query('SELECT product_name, quantity, date_time, produced_by, materials FROM production_data '
                    'WHERE id=%s', (run_id,), fetch='one')
    if not row:
        return
    product_name, quantity, date_time, by, materials = row
    if isinstance(materials, (str, bytes)):  # MySQL JSON comes back as text
        materials = json.loads(materials)

    window = Toplevel()
    window.title(f'Production #{run_id}')
    window.config(bg='white')
    center_window(window, 560, 460)
    make_label(window, 'Production Details', font=('Helvetica', 20, 'bold')).pack(pady=10)
    for text in (f'Product: {product_name}', f'Units made: {quantity}',
                 f"Date & Time: {date_time.strftime('%Y-%m-%d %H:%M:%S')}", f'Produced by: {by or ""}'):
        make_label(window, text).pack(anchor='w', padx=30)
    frame = Frame(window, bg='white')
    frame.pack(fill=BOTH, expand=True, padx=20, pady=15)
    tree = create_treeview(frame, ('material', 'quantity', 'unit'), ('Material', 'Quantity used', 'Unit'),
                           (220, 120, 80), anchors=('w', 'e', 'center'))
    fill_treeview(tree, [(m['material'], fmt_number(m['quantity']), m['unit']) for m in materials])


def production_form(window):
    """Build the Production screen inside the Admin dashboard window."""
    frame = Frame(window, width=1070, height=567, bg='white')
    frame.place(x=200, y=100)

    make_label(frame, 'Production Management', font=('Helvetica', 16, 'bold'),
               bg=BLUE, fg='white').place(x=0, y=0, relwidth=1)
    frame.back_image = PhotoImage(file='assets/back.png')  # keep a reference
    make_button(frame, image=frame.back_image, bg='white', hover='#e5e7eb',
                padx=2, pady=2, command=frame.destroy).place(x=10, y=30)

    summaries = Frame(frame, bg='white')
    summaries.place(x=30, y=100, width=500, height=100)
    make_label(summaries, 'Units made (7 days):', ('Helvetica', 14, 'bold')).grid(
        row=0, column=0, padx=10, pady=10, sticky='w')
    weekly_label = make_label(summaries, '0', fg='green')
    weekly_label.grid(row=0, column=1, sticky='w')
    make_label(summaries, 'Units made (30 days):', ('Helvetica', 14, 'bold')).grid(
        row=1, column=0, padx=10, pady=10, sticky='w')
    monthly_label = make_label(summaries, '0', fg='green')
    monthly_label.grid(row=1, column=1, sticky='w')

    records = Frame(frame, bg='white')
    records.place(x=30, y=220, width=1020, height=300)
    history_tree = create_treeview(
        records, ('id', 'product', 'quantity', 'date_time', 'by'),
        ('Run ID', 'Product', 'Units Made', 'Date & Time', 'Produced By'),
        (80, 260, 100, 180, 160), anchors=('center', 'w', 'center', 'center', 'w'))

    filter_frame = Frame(frame, bg='white')
    filter_frame.place(x=550, y=100, width=500, height=50)
    make_label(filter_frame, 'Filter:', ('Helvetica', 14, 'bold')).pack(side=LEFT, padx=10)
    filter_var = StringVar(value='all')
    frame.filter_var = filter_var  # keep a reference
    for text, value in (('All', 'all'), ('Weekly', 'weekly'), ('Monthly', 'monthly')):
        make_radio(filter_frame, text, filter_var, value,
                   lambda: update_history(history_tree, filter_var.get())).pack(side=LEFT, padx=10)

    def refresh():
        """Reload totals and the table (keeps the chosen filter)."""
        if not frame.winfo_exists():
            return  # the screen was closed meanwhile
        weekly, monthly = calculate_totals()
        weekly_label.config(text=str(weekly))
        monthly_label.config(text=str(monthly))
        update_history(history_tree, filter_var.get())

    make_button(frame, '+ New Production', font=('Helvetica', 14, 'bold'), bg='#15803d',
                command=lambda: open_new_production_window(window, on_saved=refresh)).place(x=550, y=160)

    refresh()
    history_tree.bind('<Double-1>', lambda event: open_run_details(event, history_tree))
    make_label(frame, 'Double-click a run to see the materials it used', ('Helvetica', 11), fg='grey'
               ).place(x=30, y=530)
    return frame


# ------------------------------------------------------------ Employee (operator) window
def update_clock(subtitle_label):
    """Show the current date and time and repeat every second."""
    date_time = time.strftime('%I:%M:%S %p on %A, %B %d, %Y')
    subtitle_label.config(text=f"Production Floor - {current_user['name']}\t\t\t {date_time}")
    subtitle_label.after(1000, lambda: update_clock(subtitle_label))


def employee_production_page():
    """The window Employee logins use: only the production order screen."""
    window = Tk()
    setup_theme(window)
    window.title('Production')
    window.config(bg='white')
    center_window(window, 1270, 700)
    window.grid_rowconfigure(2, weight=1)
    window.grid_columnconfigure(0, weight=1)

    window.title_image = PhotoImage(file='assets/inventory.png')  # keep a reference
    make_label(window, '\t   Manufacturing Management System', font=('Helvetica', 32, 'bold'), bg='#010c48',
               fg='white', image=window.title_image, compound=LEFT, anchor='w', padx=20
               ).grid(row=0, column=0, sticky='we')

    def confirm_exit():
        if messagebox.askyesno('Confirm Exit', 'Are you sure you want to exit?'):
            window.destroy()

    make_button(window, 'Exit', font=('Helvetica', 15, 'bold'), command=confirm_exit).place(x=1170, y=16)
    subtitle_label = make_label(window, '', font=('Helvetica', 12), bg='#4d636d', fg='white')
    subtitle_label.grid(row=1, column=0, sticky='we')
    update_clock(subtitle_label)

    container = Frame(window, bg='white')
    container.grid(row=2, column=0, sticky='nsew')
    build_production_panels(container)
    window.mainloop()


if __name__ == '__main__':
    employee_production_page()
