import re
from datetime import date
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

from tkcalendar import DateEntry  # terminal: pip install tkcalendar

from database import run_query
from ui import (make_label, make_entry, make_text, make_button, create_treeview,
                fill_treeview, selected_id, BLUE)

# Columns shown in the table (the password is not shown)
TABLE_COLUMNS = 'empid, name, email, gender, contact, education, address, doj, salary, usertype'
EDUCATION_OPTIONS = ('B.Tech', 'B.Com', 'M.Tech', 'M.Com', 'B.Sc', 'M.Sc', 'BBA', 'MBA', 'LLB', 'LLM', 'B.Arch', 'M.Arch')


def treeview_data(treeview):
    """Show all employees in the table."""
    records = run_query(f'SELECT {TABLE_COLUMNS} FROM employee_data', fetch='all')
    if records is not None:
        fill_treeview(treeview, records)


def get_form_values(fields):
    """Read all input fields and return them as a dictionary of cleaned-up text."""
    return {
        'empid': fields['empid'].get().strip(),
        'name': fields['name'].get().strip(),
        'email': fields['email'].get().strip(),
        'gender': fields['gender'].get(),
        'contact': fields['contact'].get().strip(),
        'education': fields['education'].get(),
        'address': fields['address'].get(1.0, END).strip(),
        'doj': fields['doj'].get(),
        'salary': fields['salary'].get().strip(),
        'usertype': fields['usertype'].get(),
        'password': fields['password'].get(),
    }


def validate_employee(values):
    """Check the form values. Shows an error message and returns False if something is wrong."""
    if (not values['empid'] or not values['name'] or not values['email'] or not values['contact']
            or not values['address'] or not values['salary'] or not values['password']
            or values['gender'] == 'Select Gender' or values['education'] == 'Select Education'
            or values['usertype'] == 'Select User Type'):
        messagebox.showerror('Error', 'All fields are required')
        return False

    if not values['empid'].isdigit():
        messagebox.showerror('Error', 'Employee ID must be a number')
        return False

    # Contact validation: 10 digits, starting with 6, 7, 8 or 9 (Indian mobile number)
    if not re.fullmatch(r'[6-9]\d{9}', values['contact']):
        messagebox.showerror('Error', 'Contact must be a 10 digit mobile number')
        return False

    if not re.fullmatch(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', values['email']):
        messagebox.showerror('Error', 'Enter a valid email address')
        return False

    if not values['salary'].isdigit():
        messagebox.showerror('Error', 'Salary must be a valid whole number')
        return False

    if len(values['password']) < 4:
        messagebox.showerror('Error', 'Password must be at least 4 characters long')
        return False
    return True


def clear_fields(fields, treeview, deselect_treeview=True):
    """Empty the form and (optionally) remove the selection in the table."""
    fields['empid'].delete(0, END)
    fields['name'].delete(0, END)
    fields['email'].delete(0, END)
    fields['gender'].set('Select Gender')
    fields['contact'].delete(0, END)
    fields['education'].set('Select Education')
    fields['address'].delete(1.0, END)
    fields['doj'].set_date(date.today())
    fields['salary'].delete(0, END)
    fields['usertype'].set('Select User Type')
    fields['password'].delete(0, END)
    if deselect_treeview:
        treeview.selection_remove(treeview.selection())


def select_data(event, fields, treeview):
    """When a table row is clicked, load that employee into the form."""
    empid = selected_id(treeview)
    if empid is None:
        return
    # Read the full record from the database (the table may have changed e.g. leading zeros)
    row = run_query('SELECT * FROM employee_data WHERE empid=%s', (empid,), fetch='one')
    if not row:
        return

    clear_fields(fields, treeview, deselect_treeview=False)
    fields['empid'].insert(0, row[0])
    fields['name'].insert(0, row[1])
    fields['email'].insert(0, row[2])
    fields['gender'].set(row[3])
    fields['contact'].insert(0, row[4])
    fields['education'].set(row[5])
    fields['address'].insert(1.0, row[6])
    try:
        fields['doj'].set_date(row[7])
    except ValueError:
        pass  # old record with a different date format: keep today's date
    fields['salary'].insert(0, row[8])
    fields['usertype'].set(row[9])
    fields['password'].insert(0, row[10])


def add_employee(fields, treeview):
    """Add a new employee."""
    values = get_form_values(fields)
    if not validate_employee(values):
        return

    if run_query('SELECT empid FROM employee_data WHERE empid=%s', (values['empid'],), fetch='one'):
        messagebox.showerror('Error', 'Employee ID already exists')
        return

    saved = run_query(
        '''INSERT INTO employee_data (empid, name, email, gender, contact, education, address,
                                      doj, salary, usertype, password)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (values['empid'], values['name'], values['email'], values['gender'], values['contact'],
         values['education'], values['address'], values['doj'], values['salary'],
         values['usertype'], values['password']))
    if saved:
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Data is inserted successfully')


def update_employee(fields, treeview):
    """Update the selected employee."""
    selected = selected_id(treeview)
    if selected is None:
        messagebox.showerror('Error', 'No row is selected')
        return

    values = get_form_values(fields)
    if not validate_employee(values):
        return
    if values['empid'] != str(selected):
        messagebox.showerror('Error', 'Employee ID cannot be changed. Select the row again or use Add.')
        return

    new_data = (values['name'], values['email'], values['gender'], values['contact'], values['education'],
                values['address'], values['doj'], values['salary'], values['usertype'], values['password'])

    current = run_query('SELECT name, email, gender, contact, education, address, doj, salary, usertype, password '
                        'FROM employee_data WHERE empid=%s', (selected,), fetch='one')
    if current is None:
        messagebox.showerror('Error', 'Employee not found')
        return
    if tuple(current) == new_data:
        messagebox.showinfo('Information', 'No changes detected')
        return

    saved = run_query('''UPDATE employee_data SET name=%s, email=%s, gender=%s, contact=%s, education=%s,
                         address=%s, doj=%s, salary=%s, usertype=%s, password=%s WHERE empid=%s''',
                      new_data + (selected,))
    if saved:
        treeview_data(treeview)
        messagebox.showinfo('Success', 'Data is updated successfully')


def delete_employee(fields, treeview):
    """Delete the selected employee."""
    selected = selected_id(treeview)
    if selected is None:
        messagebox.showerror('Error', 'No row is selected')
        return
    if not messagebox.askyesno('Confirm', 'Do you really want to delete the record?'):
        return

    # Never delete the last Admin: nobody could log in afterwards
    admins = run_query("SELECT COUNT(*) FROM employee_data WHERE usertype='Admin' AND empid<>%s",
                       (selected,), fetch='one')
    if admins is not None and admins[0] == 0:
        is_admin = run_query("SELECT usertype FROM employee_data WHERE empid=%s", (selected,), fetch='one')
        if is_admin and is_admin[0] == 'Admin':
            messagebox.showerror('Error', 'You cannot delete the only Admin account')
            return

    if run_query('DELETE FROM employee_data WHERE empid=%s', (selected,)):
        treeview_data(treeview)
        clear_fields(fields, treeview)
        messagebox.showinfo('Success', 'Record is deleted')


def search_employee(search_option, value, treeview):
    """Search employees by EmpId, Name, Email or Gender."""
    allowed_columns = {'EmpId': 'empid', 'Name': 'name', 'Email': 'email', 'Gender': 'gender'}
    column = allowed_columns.get(search_option)
    value = value.strip()
    if not column:
        messagebox.showerror('Error', 'No option is selected')
        return
    if not value:
        messagebox.showerror('Error', 'Enter the value to search')
        return

    records = run_query(f'SELECT {TABLE_COLUMNS} FROM employee_data WHERE {column} LIKE %s',
                        (f'%{value}%',), fetch='all')
    if records is None:
        return
    fill_treeview(treeview, records)
    if not records:
        messagebox.showinfo('Search', 'No matching employees found')


def show_all(search_combobox, search_entry, treeview):
    """Show all employees again and reset the search boxes."""
    treeview_data(treeview)
    search_combobox.set('Search By')
    search_entry.delete(0, END)


def employee_form(window):
    """Build the Employee screen inside the dashboard window."""
    employee_frame = Frame(window, width=1070, height=567, bg='white')
    employee_frame.place(x=200, y=100)

    make_label(employee_frame, 'Manage Employee Details', font=('Helvetica', 16, 'bold'),
               bg=BLUE, fg='white').place(x=0, y=0, relwidth=1)

    # ---- Top part: back button, search and table ----
    top_frame = Frame(employee_frame, bg='white')
    top_frame.place(x=0, y=40, relwidth=1, height=235)

    employee_frame.back_image = PhotoImage(file='assets/back.png')  # keep a reference
    back_button = make_button(top_frame, image=employee_frame.back_image, bg='white', hover='#e5e7eb',
                              padx=2, pady=2, command=employee_frame.destroy)
    back_button.place(x=10, y=0)

    search_frame = Frame(top_frame, bg='white')
    search_frame.pack()

    search_combobox = ttk.Combobox(search_frame, values=('EmpId', 'Name', 'Email', 'Gender'),
                                   font=('Helvetica', 12), state='readonly')
    search_combobox.set('Search By')
    search_combobox.grid(row=0, column=0, padx=20)

    search_entry = make_entry(search_frame, font=('Helvetica', 12))
    search_entry.grid(row=0, column=1)

    treeview = create_treeview(
        top_frame,
        columns=('empId', 'name', 'email', 'gender', 'contact', 'education', 'address', 'doj', 'salary', 'usertype'),
        headings=('EmpId', 'Name', 'Email', 'Gender', 'Contact', 'Education', 'Address', 'Date of Joining',
                  'Salary', 'User Type'),
        widths=(60, 140, 180, 80, 100, 120, 200, 100, 140, 120))

    make_button(search_frame, 'Search', font=('Helvetica', 12), width=10,
                command=lambda: search_employee(search_combobox.get(), search_entry.get(), treeview)
                ).grid(row=0, column=2, padx=20)
    make_button(search_frame, 'Show All', font=('Helvetica', 12), width=10,
                command=lambda: show_all(search_combobox, search_entry, treeview)
                ).grid(row=0, column=3)

    # ---- Middle part: the input form ----
    detail_frame = Frame(employee_frame, bg='white')
    detail_frame.place(x=20, y=280)
    small = ('Helvetica', 12)
    fields = {}

    make_label(detail_frame, 'EmpId', small).grid(row=0, column=0, padx=20, pady=10, sticky='w')
    fields['empid'] = make_entry(detail_frame, small)
    fields['empid'].grid(row=0, column=1, padx=20, pady=10)

    make_label(detail_frame, 'Name', small).grid(row=0, column=2, padx=20, pady=10, sticky='w')
    fields['name'] = make_entry(detail_frame, small)
    fields['name'].grid(row=0, column=3, padx=20, pady=10)

    make_label(detail_frame, 'Email', small).grid(row=0, column=4, padx=20, pady=10, sticky='w')
    fields['email'] = make_entry(detail_frame, small)
    fields['email'].grid(row=0, column=5, padx=20, pady=10)

    make_label(detail_frame, 'Gender', small).grid(row=1, column=0, padx=20, pady=10, sticky='w')
    fields['gender'] = ttk.Combobox(detail_frame, values=('Male', 'Female'), font=small, width=18, state='readonly')
    fields['gender'].set('Select Gender')
    fields['gender'].grid(row=1, column=1)

    make_label(detail_frame, 'Contact', small).grid(row=1, column=2, padx=20, pady=10, sticky='w')
    fields['contact'] = make_entry(detail_frame, small)
    fields['contact'].grid(row=1, column=3, padx=20, pady=10)

    make_label(detail_frame, 'Salary', small).grid(row=1, column=4, padx=20, pady=10, sticky='w')
    fields['salary'] = make_entry(detail_frame, small)
    fields['salary'].grid(row=1, column=5, padx=20, pady=10)

    make_label(detail_frame, 'Education', small).grid(row=2, column=0, padx=20, pady=10, sticky='w')
    fields['education'] = ttk.Combobox(detail_frame, values=EDUCATION_OPTIONS, font=small, width=18, state='readonly')
    fields['education'].set('Select Education')
    fields['education'].grid(row=2, column=1)

    make_label(detail_frame, 'Address', small).grid(row=2, column=2, padx=20, pady=10, sticky='w')
    fields['address'] = make_text(detail_frame, width=20, height=3, font=small)
    fields['address'].grid(row=2, column=3, rowspan=2)

    make_label(detail_frame, 'User Type', small).grid(row=2, column=4, padx=20, pady=10, sticky='w')
    fields['usertype'] = ttk.Combobox(detail_frame, values=('Admin', 'Employee'), font=small, width=18,
                                      state='readonly')
    fields['usertype'].set('Select User Type')
    fields['usertype'].grid(row=2, column=5)

    make_label(detail_frame, 'Date of Joining', small).grid(row=3, column=0, padx=20, pady=10, sticky='w')
    fields['doj'] = DateEntry(detail_frame, width=18, font=small, state='readonly', date_pattern='dd/mm/yyyy',
                              background=BLUE, foreground='white', selectbackground=BLUE,
                              selectforeground='white', normalbackground='white', normalforeground='black',
                              weekendbackground='white', weekendforeground='black',
                              headersbackground='#e5e7eb', headersforeground='black')
    fields['doj'].grid(row=3, column=1)

    make_label(detail_frame, 'Password', small).grid(row=3, column=4, padx=20, pady=10, sticky='w')
    fields['password'] = make_entry(detail_frame, small, show='*')
    fields['password'].grid(row=3, column=5, padx=20, pady=10)
    make_label(detail_frame, 'must be at least 4 characters', ('Helvetica', 10), fg='grey'
               ).grid(row=4, column=5, padx=20, sticky='w')

    # ---- Bottom part: buttons ----
    button_frame = Frame(employee_frame, bg='white')
    button_frame.place(x=200, y=520)
    buttons = [
        ('Add', lambda: add_employee(fields, treeview)),
        ('Update', lambda: update_employee(fields, treeview)),
        ('Delete', lambda: delete_employee(fields, treeview)),
        ('Clear', lambda: clear_fields(fields, treeview)),
    ]
    for column, (text, command) in enumerate(buttons):
        make_button(button_frame, text, font=('Helvetica', 12), width=10, command=command
                    ).grid(row=0, column=column, padx=20)

    treeview_data(treeview)
    treeview.bind('<ButtonRelease-1>', lambda event: select_data(event, fields, treeview))
    return employee_frame
