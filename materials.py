from tkinter import *
from tkinter import ttk
from tkinter import messagebox, simpledialog

from database import run_query
from ui import (make_label, make_entry, make_button, create_treeview, selected_id, fmt_number, BLUE)

UNITS = ('kg', 'g', 'litre', 'ml', 'pcs', 'metre', 'box', 'sheet')
SEARCH_COLUMNS = {'Name': 'name', 'Supplier': 'supplier', 'Unit': 'unit'}
SELECT = 'SELECT id, name, unit, quantity, reorder_level, cost, supplier FROM material_data'


def show_materials(treeview, records):
    """Fill the table. Materials at or below their reorder level are marked LOW (red)."""
    treeview.delete(*treeview.get_children())
    for material_id, name, unit, quantity, reorder, cost, supplier in records:
        low = quantity <= reorder
        treeview.insert('', END, tags=('low',) if low else (), values=(
            material_id, name, unit, fmt_number(quantity), fmt_number(reorder),
            f'{float(cost):.2f}', supplier or '', 'LOW' if low else 'OK'))


def treeview_data(treeview):
    """Show all materials in the table."""
    records = run_query(SELECT + ' ORDER BY name', fetch='all')
    if records is not None:
        show_materials(treeview, records)


def fetch_suppliers(supplier_combobox):
    """Fill the Supplier dropdown from the suppliers screen data."""
    rows = run_query('SELECT name FROM supplier_data ORDER BY name', fetch='all') or []
    supplier_combobox.config(values=[row[0] for row in rows])
    supplier_combobox.set('Select')


def clear_fields(fields, treeview):
    """Empty the form and remove the selection in the table."""
    treeview.selection_remove(treeview.selection())
    fields['name'].delete(0, END)
    fields['unit'].set('Select Unit')
    fields['quantity'].delete(0, END)
    fields['reorder'].delete(0, END)
    fields['cost'].delete(0, END)
    fields['supplier'].set('Select')


def read_and_validate(fields):
    """Return (name, unit, quantity, reorder, cost, supplier) or None if the input is wrong."""
    name = fields['name'].get().strip()
    unit = fields['unit'].get().strip()
    supplier = fields['supplier'].get().strip()
    if supplier in ('Select', 'Empty'):
        supplier = ''
    if not name or unit == 'Select Unit' or not unit:
        messagebox.showerror('Error', 'Material name and unit are required.')
        return None
    try:
        quantity = round(float(fields['quantity'].get().strip()), 3)
        reorder = round(float(fields['reorder'].get().strip()), 3)
        cost = round(float(fields['cost'].get().strip()), 2)
        if quantity < 0 or reorder < 0 or cost < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror('Error', 'Stock, reorder level and cost must be valid non-negative numbers.')
        return None
    return name, unit, quantity, reorder, cost, supplier


def select_data(event, fields, treeview):
    """When a row is clicked, load that material into the form."""
    material_id = selected_id(treeview)
    if material_id is None:
        return
    row = run_query(SELECT + ' WHERE id=%s', (material_id,), fetch='one')
    if not row:
        return
    _, name, unit, quantity, reorder, cost, supplier = row
    for key in ('name', 'quantity', 'reorder', 'cost'):
        fields[key].delete(0, END)
    fields['name'].insert(0, name)
    fields['unit'].set(unit)
    fields['quantity'].insert(0, fmt_number(quantity))
    fields['reorder'].insert(0, fmt_number(reorder))
    fields['cost'].insert(0, f'{float(cost):.2f}')
    fields['supplier'].set(supplier or 'Select')


def add_material(fields, treeview):
    """Add a new raw material."""
    data = read_and_validate(fields)
    if data is None:
        return
    if run_query('SELECT id FROM material_data WHERE name=%s', (data[0],), fetch='one'):
        messagebox.showerror('Error', 'Material already exists.')
        return
    if run_query('INSERT INTO material_data (name, unit, quantity, reorder_level, cost, supplier) '
                 'VALUES (%s, %s, %s, %s, %s, %s)', data):
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Material added successfully.')


def update_material(fields, treeview):
    """Update the selected material."""
    material_id = selected_id(treeview)
    if material_id is None:
        messagebox.showerror('Error', 'No row is selected')
        return
    data = read_and_validate(fields)
    if data is None:
        return
    if run_query('SELECT id FROM material_data WHERE name=%s AND id<>%s', (data[0], material_id), fetch='one'):
        messagebox.showerror('Error', 'Another material already has this name.')
        return
    if run_query('UPDATE material_data SET name=%s, unit=%s, quantity=%s, reorder_level=%s, cost=%s, '
                 'supplier=%s WHERE id=%s', data + (material_id,)):
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Material updated successfully.')


def delete_material(fields, treeview):
    """Delete the selected material (only if no product recipe uses it)."""
    material_id = selected_id(treeview)
    if material_id is None:
        messagebox.showerror('Error', 'No row is selected')
        return
    used = run_query('SELECT COUNT(*) FROM bom_data WHERE material_id=%s', (material_id,), fetch='one')
    if used and used[0] > 0:
        messagebox.showerror('Error', f'This material is used in the recipe of {used[0]} product(s).\n'
                                      'Remove it from those recipes first.')
        return
    if not messagebox.askyesno('Confirm', 'Do you really want to delete this material?'):
        return
    if run_query('DELETE FROM material_data WHERE id=%s', (material_id,)):
        treeview_data(treeview)
        clear_fields(fields, treeview)
        messagebox.showinfo('Success', 'Material is deleted.')


def receive_stock(fields, treeview):
    """Add newly purchased quantity to the stock of the selected material."""
    material_id = selected_id(treeview)
    if material_id is None:
        messagebox.showerror('Error', 'Select a material in the table first.')
        return
    row = run_query('SELECT name, unit FROM material_data WHERE id=%s', (material_id,), fetch='one')
    if not row:
        return
    amount = simpledialog.askfloat('Receive Stock', f'Quantity received for {row[0]} ({row[1]}):',
                                   minvalue=0.001, maxvalue=10000000)
    if amount is None:
        return
    if run_query('UPDATE material_data SET quantity = quantity + %s WHERE id=%s', (round(amount, 3), material_id)):
        treeview_data(treeview)
        clear_fields(fields, treeview)
        messagebox.showinfo('Success', f'{fmt_number(amount)} {row[1]} added to stock.')


def search_material(search_combobox, search_entry, treeview):
    """Search materials by Name, Supplier or Unit."""
    column = SEARCH_COLUMNS.get(search_combobox.get().strip())
    value = search_entry.get().strip()
    if not column:
        messagebox.showwarning('Warning', 'Please select an option')
        return
    if not value:
        messagebox.showwarning('Warning', 'Please enter the value to search')
        return
    records = run_query(f'{SELECT} WHERE {column} LIKE %s ORDER BY name', (f'%{value}%',), fetch='all')
    if records is None:
        return
    show_materials(treeview, records)
    if not records:
        messagebox.showinfo('Search', 'No matching materials found.')


def show_low_stock(treeview):
    """Show only the materials that need to be re-ordered."""
    records = run_query(SELECT + ' WHERE quantity <= reorder_level ORDER BY name', fetch='all')
    if records is None:
        return
    show_materials(treeview, records)
    if not records:
        messagebox.showinfo('Stock', 'No material is low on stock.')


def show_all(treeview, search_combobox, search_entry):
    """Show all materials again and reset the search boxes."""
    treeview_data(treeview)
    search_combobox.set('Search By')
    search_entry.delete(0, END)


def material_form(window):
    """Build the Raw Materials screen inside the dashboard window."""
    material_frame = Frame(window, width=1070, height=567, bg='white')
    material_frame.place(x=200, y=100)

    material_frame.back_image = PhotoImage(file='assets/back.png')  # keep a reference
    make_button(material_frame, image=material_frame.back_image, bg='white', hover='#e5e7eb',
                padx=2, pady=2, command=material_frame.destroy).place(x=10, y=0)

    # ---- Left side: input form ----
    left_frame = Frame(material_frame, bg='white', bd=2, relief=RIDGE)
    left_frame.place(x=20, y=40)
    make_label(left_frame, 'Manage Raw Materials', font=('Helvetica', 16, 'bold'),
               bg=BLUE, fg='white').grid(row=0, columnspan=2, sticky='we')

    font = ('Helvetica', 13, 'bold')
    fields = {}
    make_label(left_frame, 'Material Name', font).grid(row=1, column=0, padx=20, pady=12, sticky='w')
    fields['name'] = make_entry(left_frame, font)
    fields['name'].grid(row=1, column=1, padx=10)

    make_label(left_frame, 'Unit', font).grid(row=2, column=0, padx=20, pady=12, sticky='w')
    fields['unit'] = ttk.Combobox(left_frame, values=UNITS, font=font, width=18, state='readonly')
    fields['unit'].set('Select Unit')
    fields['unit'].grid(row=2, column=1)

    make_label(left_frame, 'Stock', font).grid(row=3, column=0, padx=20, pady=12, sticky='w')
    fields['quantity'] = make_entry(left_frame, font)
    fields['quantity'].grid(row=3, column=1)

    make_label(left_frame, 'Reorder Level', font).grid(row=4, column=0, padx=20, pady=12, sticky='w')
    fields['reorder'] = make_entry(left_frame, font)
    fields['reorder'].grid(row=4, column=1)

    make_label(left_frame, 'Cost per Unit', font).grid(row=5, column=0, padx=20, pady=12, sticky='w')
    fields['cost'] = make_entry(left_frame, font)
    fields['cost'].grid(row=5, column=1)

    make_label(left_frame, 'Supplier', font).grid(row=6, column=0, padx=20, pady=12, sticky='w')
    fields['supplier'] = ttk.Combobox(left_frame, font=font, width=18, state='readonly')
    fields['supplier'].grid(row=6, column=1)

    # ---- Right side: search and table ----
    search_frame = LabelFrame(material_frame, text='Search Material', font=('Helvetica', 14, 'bold'),
                              bg='white', fg='#1f2937')
    search_frame.place(x=480, y=10)
    search_combobox = ttk.Combobox(search_frame, values=tuple(SEARCH_COLUMNS), state='readonly',
                                   width=14, font=('Helvetica', 13))
    search_combobox.set('Search By')
    search_combobox.grid(row=0, column=0, padx=10, pady=5)
    search_entry = make_entry(search_frame, ('Helvetica', 13), width=16)
    search_entry.grid(row=0, column=1, padx=10)

    table_frame = Frame(material_frame, bg='white')
    table_frame.place(x=480, y=130, width=570, height=420)
    treeview = create_treeview(
        table_frame, ('id', 'name', 'unit', 'quantity', 'reorder', 'cost', 'supplier', 'status'),
        ('Id', 'Material', 'Unit', 'Stock', 'Reorder', 'Cost', 'Supplier', 'Status'),
        (35, 110, 50, 65, 65, 60, 100, 55), anchors=('center', 'w', 'center', 'e', 'e', 'e', 'w', 'center'))
    treeview.tag_configure('low', foreground='#b91c1c')

    search_buttons = Frame(search_frame, bg='white')
    search_buttons.grid(row=1, column=0, columnspan=2, pady=(0, 6))
    make_button(search_buttons, 'Search', font=('Helvetica', 12), width=8, command=lambda: search_material(
        search_combobox, search_entry, treeview)).grid(row=0, column=0, padx=6)
    make_button(search_buttons, 'Show All', font=('Helvetica', 12), width=8, command=lambda: show_all(
        treeview, search_combobox, search_entry)).grid(row=0, column=1, padx=6)
    make_button(search_buttons, 'Low Stock', font=('Helvetica', 12), width=8, bg='#b91c1c',
                command=lambda: show_low_stock(treeview)).grid(row=0, column=2, padx=6)

    # ---- Buttons under the form ----
    button_frame = Frame(left_frame, bg='white')
    button_frame.grid(row=7, columnspan=2, pady=(15, 10))
    buttons = [
        ('Add', lambda: add_material(fields, treeview)),
        ('Update', lambda: update_material(fields, treeview)),
        ('Delete', lambda: delete_material(fields, treeview)),
        ('Clear', lambda: clear_fields(fields, treeview)),
    ]
    for column, (text, command) in enumerate(buttons):
        make_button(button_frame, text, width=6, command=command).grid(row=0, column=column, padx=5)
    make_button(button_frame, 'Receive Stock (+)', width=22, bg='#15803d',
                command=lambda: receive_stock(fields, treeview)).grid(row=1, column=0, columnspan=4, pady=10)

    fetch_suppliers(fields['supplier'])
    treeview_data(treeview)
    treeview.bind('<ButtonRelease-1>', lambda event: select_data(event, fields, treeview))
    return material_frame
