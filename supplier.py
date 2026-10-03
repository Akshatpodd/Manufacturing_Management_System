import re
from tkinter import *
from tkinter import messagebox

from database import run_query
from ui import (make_label, make_entry, make_text, make_button, create_treeview,
                fill_treeview, selected_id, BLUE)


def treeview_data(treeview):
    """Show all suppliers in the table."""
    records = run_query('SELECT invoice, name, contact, description FROM supplier_data', fetch='all')
    if records is not None:
        fill_treeview(treeview, records)


def clear(fields, treeview, deselect_treeview=True):
    """Empty the form and (optionally) remove the selection in the table."""
    fields['invoice'].delete(0, END)
    fields['name'].delete(0, END)
    fields['contact'].delete(0, END)
    fields['description'].delete(1.0, END)
    if deselect_treeview:
        treeview.selection_remove(treeview.selection())


def read_fields(fields):
    """Return (invoice, name, contact, description) from the form."""
    return (fields['invoice'].get().strip(), fields['name'].get().strip(),
            fields['contact'].get().strip(), fields['description'].get(1.0, END).strip())


def validate_supplier(invoice, name, contact, description):
    """Check the form values. Shows an error and returns False if something is wrong."""
    if not invoice or not name or not contact or not description:
        messagebox.showerror('Error', 'All fields are required.')
        return False
    if not invoice.isdigit():
        messagebox.showerror('Error', 'Invoice number must be a number.')
        return False
    if not re.fullmatch(r'[6-9]\d{9}', contact):
        messagebox.showerror('Error', 'Contact must be a 10 digit mobile number.')
        return False
    return True


def select_data(event, fields, treeview):
    """When a row is clicked, load it into the form."""
    selection = treeview.selection()
    if not selection:
        return
    row = treeview.item(selection[0])['values']
    clear(fields, treeview, deselect_treeview=False)
    fields['invoice'].insert(0, row[0])
    fields['name'].insert(0, row[1])
    fields['contact'].insert(0, str(row[2]))
    fields['description'].insert(1.0, row[3])


def add_supplier(fields, treeview):
    """Add a new supplier."""
    invoice, name, contact, description = read_fields(fields)
    if not validate_supplier(invoice, name, contact, description):
        return
    if run_query('SELECT invoice FROM supplier_data WHERE invoice=%s', (invoice,), fetch='one'):
        messagebox.showerror('Error', 'Invoice number already exists.')
        return

    if run_query('INSERT INTO supplier_data (invoice, name, contact, description) VALUES (%s, %s, %s, %s)',
                 (invoice, name, contact, description)):
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Supplier added successfully.')


def update_supplier(fields, treeview):
    """Update the selected supplier."""
    if selected_id(treeview) is None:
        messagebox.showerror('Error', 'No row is selected for update.')
        return
    invoice, name, contact, description = read_fields(fields)
    if not validate_supplier(invoice, name, contact, description):
        return

    current = run_query('SELECT name, contact, description FROM supplier_data WHERE invoice=%s',
                        (invoice,), fetch='one')
    if current is None:
        messagebox.showerror('Error', 'Supplier not found.')
        return
    if tuple(current) == (name, contact, description):
        messagebox.showinfo('Info', 'No changes detected.')
        return

    if run_query('UPDATE supplier_data SET name=%s, contact=%s, description=%s WHERE invoice=%s',
                 (name, contact, description, invoice)):
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Supplier details updated successfully.')


def delete_supplier(fields, treeview):
    """Delete the selected supplier."""
    invoice = selected_id(treeview)
    if invoice is None:
        messagebox.showerror('Error', 'No row is selected.')
        return
    if not messagebox.askyesno('Confirm Deletion', 'Do you really want to delete the selected record?'):
        return

    if run_query('DELETE FROM supplier_data WHERE invoice=%s', (invoice,)):
        treeview_data(treeview)
        clear(fields, treeview)
        messagebox.showinfo('Success', 'Record has been deleted successfully.')


def supplier_form(window):
    """Build the Supplier screen inside the dashboard window."""
    supplier_frame = Frame(window, width=1070, height=567, bg='white')
    supplier_frame.place(x=200, y=100)

    make_label(supplier_frame, 'Manage Supplier Details', font=('Helvetica', 16, 'bold'),
               bg=BLUE, fg='white').place(x=0, y=0, relwidth=1)

    supplier_frame.back_image = PhotoImage(file='assets/back.png')  # keep a reference
    make_button(supplier_frame, image=supplier_frame.back_image, bg='white', hover='#e5e7eb',
                padx=2, pady=2, command=supplier_frame.destroy).place(x=10, y=30)

    # ---- Input form ----
    left_frame = Frame(supplier_frame, bg='white')
    left_frame.place(x=10, y=100)
    fields = {}
    font = ('Helvetica', 14, 'bold')

    make_label(left_frame, 'Invoice No.', font).grid(row=0, column=0, padx=(20, 40), sticky='w')
    fields['invoice'] = make_entry(left_frame, font)
    fields['invoice'].grid(row=0, column=1)

    make_label(left_frame, 'Supplier Name', font).grid(row=1, column=0, padx=(20, 40), pady=25, sticky='w')
    fields['name'] = make_entry(left_frame, font)
    fields['name'].grid(row=1, column=1)

    make_label(left_frame, 'Supplier Contact', font).grid(row=2, column=0, padx=(20, 40), sticky='w')
    fields['contact'] = make_entry(left_frame, font)
    fields['contact'].grid(row=2, column=1)

    make_label(left_frame, 'Description', font).grid(row=3, column=0, padx=(20, 40), pady=25, sticky='nw')
    fields['description'] = make_text(left_frame, width=25, height=6)
    fields['description'].grid(row=3, column=1, pady=25)

    # ---- Table ----
    right_frame = Frame(supplier_frame, bg='white')
    right_frame.place(x=520, y=95, width=500, height=345)
    treeview = create_treeview(right_frame, ('invoice', 'name', 'contact', 'description'),
                               ('Invoice ID', 'Supplier Name', 'Supplier Contact', 'Description'),
                               (80, 160, 120, 300))

    # ---- Buttons ----
    button_frame = Frame(left_frame, bg='white')
    button_frame.grid(row=4, columnspan=2, pady=20)
    buttons = [
        ('Add', lambda: add_supplier(fields, treeview)),
        ('Update', lambda: update_supplier(fields, treeview)),
        ('Delete', lambda: delete_supplier(fields, treeview)),
        ('Clear', lambda: clear(fields, treeview)),
    ]
    for column, (text, command) in enumerate(buttons):
        make_button(button_frame, text, width=8, command=command).grid(row=0, column=column, padx=10)

    treeview_data(treeview)
    treeview.bind('<ButtonRelease-1>', lambda event: select_data(event, fields, treeview))
    return supplier_frame
