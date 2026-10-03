from tkinter import *
from tkinter import ttk
from tkinter import messagebox

from database import run_query
from ui import (make_label, make_entry, make_button, create_treeview, fill_treeview,
                selected_id, fmt_number, BLUE)


# ---------------------------------------------------------------- products
def treeview_data(treeview):
    """Show all finished products in the table."""
    records = run_query('SELECT id, name, price, quantity FROM product_data ORDER BY name', fetch='all')
    if records is not None:
        fill_treeview(treeview, [(pid, name, f'{float(price):.2f}', qty) for pid, name, price, qty in records])


def clear_fields(fields, treeview, recipe_tree):
    """Empty the form, the selection and the recipe table."""
    treeview.selection_remove(treeview.selection())
    fields['name'].delete(0, END)
    fields['price'].delete(0, END)
    fields['quantity'].delete(0, END)
    recipe_tree.delete(*recipe_tree.get_children())


def read_and_validate(fields):
    """Return (name, price, quantity) or None if the input is wrong."""
    name = fields['name'].get().strip()
    if not name:
        messagebox.showerror('Error', 'Product name is required.')
        return None
    try:
        price = round(float(fields['price'].get().strip()), 2)
        quantity = int(fields['quantity'].get().strip() or 0)
        if price < 0 or quantity < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror('Error', 'Price must be a number and stock a whole number (not negative).')
        return None
    return name, price, quantity


def load_recipe(recipe_tree, product_id):
    """Show the recipe (materials needed for ONE unit) of a product."""
    records = run_query('SELECT m.name, b.qty_per_unit, m.unit FROM bom_data b '
                        'JOIN material_data m ON m.id = b.material_id WHERE b.product_id=%s ORDER BY m.name',
                        (product_id,), fetch='all') or []
    fill_treeview(recipe_tree, [(name, fmt_number(qty), unit) for name, qty, unit in records])


def select_data(event, fields, treeview, recipe_tree):
    """When a product row is clicked, load it into the form and show its recipe."""
    product_id = selected_id(treeview)
    if product_id is None:
        return
    row = run_query('SELECT name, price, quantity FROM product_data WHERE id=%s', (product_id,), fetch='one')
    if not row:
        return
    for key in ('name', 'price', 'quantity'):
        fields[key].delete(0, END)
    fields['name'].insert(0, row[0])
    fields['price'].insert(0, f'{float(row[1]):.2f}')
    fields['quantity'].insert(0, row[2])
    load_recipe(recipe_tree, product_id)


def add_product(fields, treeview, recipe_tree):
    """Add a new finished product."""
    data = read_and_validate(fields)
    if data is None:
        return
    if run_query('SELECT id FROM product_data WHERE name=%s', (data[0],), fetch='one'):
        messagebox.showerror('Error', 'Product already exists.')
        return
    if run_query('INSERT INTO product_data (name, price, quantity) VALUES (%s, %s, %s)', data):
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Product added. Now select it and add its recipe on the right.')


def update_product(fields, treeview):
    """Update the selected product."""
    product_id = selected_id(treeview)
    if product_id is None:
        messagebox.showerror('Error', 'No row is selected')
        return
    data = read_and_validate(fields)
    if data is None:
        return
    if run_query('SELECT id FROM product_data WHERE name=%s AND id<>%s', (data[0], product_id), fetch='one'):
        messagebox.showerror('Error', 'Another product already has this name.')
        return
    if run_query('UPDATE product_data SET name=%s, price=%s, quantity=%s WHERE id=%s', data + (product_id,)):
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Product updated successfully.')


def delete_product(fields, treeview, recipe_tree):
    """Delete the selected product (its recipe is deleted with it)."""
    product_id = selected_id(treeview)
    if product_id is None:
        messagebox.showerror('Error', 'No row is selected')
        return
    if not messagebox.askyesno('Confirm', 'Delete this product and its recipe?\n(Production history is kept.)'):
        return
    if run_query('DELETE FROM product_data WHERE id=%s', (product_id,)):
        treeview_data(treeview)
        clear_fields(fields, treeview, recipe_tree)
        messagebox.showinfo('Success', 'Product is deleted.')


# ---------------------------------------------------------------- recipe
def save_recipe_item(treeview, recipe_tree, material_combobox, quantity_entry):
    """Add a material to the recipe of the selected product (or change its quantity)."""
    product_id = selected_id(treeview)
    if product_id is None:
        messagebox.showerror('Error', 'Select a product in the table first.')
        return
    material_name = material_combobox.get().strip()
    material = run_query('SELECT id FROM material_data WHERE name=%s', (material_name,), fetch='one')
    if not material:
        messagebox.showerror('Error', 'Please select a material.')
        return
    try:
        qty = round(float(quantity_entry.get().strip()), 3)
        if qty <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror('Error', 'Quantity per unit must be a number greater than 0.')
        return

    existing = run_query('SELECT id FROM bom_data WHERE product_id=%s AND material_id=%s',
                         (product_id, material[0]), fetch='one')
    if existing:
        saved = run_query('UPDATE bom_data SET qty_per_unit=%s WHERE id=%s', (qty, existing[0]))
    else:
        saved = run_query('INSERT INTO bom_data (product_id, material_id, qty_per_unit) VALUES (%s, %s, %s)',
                          (product_id, material[0], qty))
    if saved:
        load_recipe(recipe_tree, product_id)
        quantity_entry.delete(0, END)


def remove_recipe_item(treeview, recipe_tree):
    """Remove the selected material from the recipe."""
    product_id = selected_id(treeview)
    selection = recipe_tree.selection()
    if product_id is None or not selection:
        messagebox.showerror('Error', 'Select a recipe row to remove.')
        return
    material_name = recipe_tree.item(selection[0])['values'][0]
    if run_query('DELETE FROM bom_data WHERE product_id=%s AND material_id='
                 '(SELECT id FROM material_data WHERE name=%s)', (product_id, str(material_name))):
        load_recipe(recipe_tree, product_id)


def select_recipe_row(event, recipe_tree, material_combobox, quantity_entry):
    """Clicking a recipe row loads it into the small recipe form so it can be changed."""
    selection = recipe_tree.selection()
    if not selection:
        return
    name, qty, _unit = recipe_tree.item(selection[0])['values']
    material_combobox.set(name)
    quantity_entry.delete(0, END)
    quantity_entry.insert(0, qty)


def product_form(window):
    """Build the Products + Recipe screen inside the dashboard window."""
    product_frame = Frame(window, width=1070, height=567, bg='white')
    product_frame.place(x=200, y=100)

    product_frame.back_image = PhotoImage(file='assets/back.png')  # keep a reference
    make_button(product_frame, image=product_frame.back_image, bg='white', hover='#e5e7eb',
                padx=2, pady=2, command=product_frame.destroy).place(x=10, y=0)

    # ---- Left side: product form ----
    left_frame = Frame(product_frame, bg='white', bd=2, relief=RIDGE)
    left_frame.place(x=20, y=40)
    make_label(left_frame, 'Manage Products', font=('Helvetica', 16, 'bold'),
               bg=BLUE, fg='white').grid(row=0, columnspan=2, sticky='we')

    font = ('Helvetica', 13, 'bold')
    fields = {}
    make_label(left_frame, 'Product Name', font).grid(row=1, column=0, padx=20, pady=20, sticky='w')
    fields['name'] = make_entry(left_frame, font, width=18)
    fields['name'].grid(row=1, column=1, padx=10)
    make_label(left_frame, 'Price', font).grid(row=2, column=0, padx=20, pady=20, sticky='w')
    fields['price'] = make_entry(left_frame, font, width=18)
    fields['price'].grid(row=2, column=1)
    make_label(left_frame, 'Stock', font).grid(row=3, column=0, padx=20, pady=20, sticky='w')
    fields['quantity'] = make_entry(left_frame, font, width=18)
    fields['quantity'].grid(row=3, column=1)
    make_label(left_frame, 'Stock goes up by itself when you run production.', ('Helvetica', 10), fg='grey'
               ).grid(row=4, columnspan=2, padx=20, sticky='w')

    # ---- Right side top: products table ----
    table_frame = Frame(product_frame, bg='white')
    table_frame.place(x=480, y=40, width=570, height=190)
    treeview = create_treeview(table_frame, ('id', 'name', 'price', 'quantity'),
                               ('Id', 'Product', 'Price', 'Stock'), (40, 250, 100, 100),
                               anchors=('center', 'w', 'e', 'center'))

    # ---- Right side bottom: recipe ----
    recipe_box = LabelFrame(product_frame, text='Recipe: materials needed for ONE unit of the selected product',
                            font=('Helvetica', 12, 'bold'), bg='white', fg='#1f2937')
    recipe_box.place(x=480, y=245, width=570, height=300)

    controls = Frame(recipe_box, bg='white')
    controls.pack(fill='x', pady=6)
    material_combobox = ttk.Combobox(controls, font=('Helvetica', 12), width=16, state='readonly')
    material_combobox.set('Select material')
    material_combobox.grid(row=0, column=0, padx=6)
    materials = run_query('SELECT name FROM material_data ORDER BY name', fetch='all') or []
    material_combobox.config(values=[row[0] for row in materials])
    quantity_entry = make_entry(controls, ('Helvetica', 12), width=8)
    quantity_entry.grid(row=0, column=1, padx=6)
    make_label(controls, 'per unit', ('Helvetica', 11), fg='grey').grid(row=0, column=2)

    recipe_frame = Frame(recipe_box, bg='white')
    recipe_frame.pack(fill=BOTH, expand=1, padx=4, pady=4)
    recipe_tree = create_treeview(recipe_frame, ('material', 'qty', 'unit'),
                                  ('Material', 'Qty per unit', 'Unit'), (250, 120, 80),
                                  anchors=('w', 'e', 'center'))
    make_button(controls, 'Save', font=('Helvetica', 12), width=6, command=lambda: save_recipe_item(
        treeview, recipe_tree, material_combobox, quantity_entry)).grid(row=0, column=3, padx=6)
    make_button(controls, 'Remove', font=('Helvetica', 12), width=7, bg='#b91c1c', command=lambda: remove_recipe_item(
        treeview, recipe_tree)).grid(row=0, column=4, padx=6)
    recipe_tree.bind('<ButtonRelease-1>', lambda event: select_recipe_row(
        event, recipe_tree, material_combobox, quantity_entry))

    # ---- Buttons under the product form ----
    button_frame = Frame(left_frame, bg='white')
    button_frame.grid(row=5, columnspan=2, pady=20)
    buttons = [
        ('Add', lambda: add_product(fields, treeview, recipe_tree)),
        ('Update', lambda: update_product(fields, treeview)),
        ('Delete', lambda: delete_product(fields, treeview, recipe_tree)),
        ('Clear', lambda: clear_fields(fields, treeview, recipe_tree)),
    ]
    for column, (text, command) in enumerate(buttons):
        make_button(button_frame, text, width=6, command=command).grid(row=0, column=column, padx=5)

    treeview_data(treeview)
    treeview.bind('<ButtonRelease-1>', lambda event: select_data(event, fields, treeview, recipe_tree))
    return product_frame
