from tkinter import *
from tkinter import messagebox

from database import connect_database, initialize_database, current_user
from ui import setup_theme, center_window, make_label, make_entry, make_button, BLUE
from dashboard import create_window
from production import employee_production_page


def check_login(employee_id, password, login_window, result):
    """Check the Employee ID and password. On success remember who logged in and close the login window."""
    employee_id = employee_id.strip()
    if not employee_id or not password:
        messagebox.showerror('Error', 'Please enter Employee ID and Password')
        return
    if not employee_id.isdigit():
        messagebox.showerror('Error', 'Employee ID must be a number')
        return

    cursor, connection = connect_database()
    if not cursor or not connection:
        return  # connect_database already showed the error

    try:
        cursor.execute('SELECT name, usertype FROM employee_data WHERE empid=%s AND password=%s',
                       (int(employee_id), password))
        row = cursor.fetchone()
    except Exception as e:
        messagebox.showerror('Error', f'Error due to {e}')
        return
    finally:
        cursor.close()
        connection.close()

    if not row:
        messagebox.showerror('Error', 'Invalid Employee ID or Password')
    elif row[1] in ('Admin', 'Employee'):
        current_user['name'] = row[0]
        result['usertype'] = row[1]  # login_form opens the right page after this window closes
        login_window.destroy()
    else:
        messagebox.showerror('Error', 'Invalid UserType')


def login_form():
    """Show the login window. After a successful login, open the Admin dashboard or the production page."""
    login_window = Tk()
    setup_theme(login_window)
    login_window.title('Login')
    login_window.resizable(False, False)
    login_window.config(bg='white')
    center_window(login_window, 640, 400)

    # Creates the database and tables on first run (and a default Admin if there are no employees)
    if not initialize_database():
        login_window.destroy()
        return

    result = {'usertype': None}

    make_label(login_window, 'Manufacturing Management System', font=('Helvetica', 22, 'bold'),
               bg=BLUE, fg='white').pack(pady=10, fill='x')

    frame = Frame(login_window, bg='white')
    frame.pack(padx=20, pady=20)

    try:
        login_window.login_image = PhotoImage(file='assets/login.png')  # keep a reference
        Label(frame, image=login_window.login_image, bg='white').grid(row=0, column=0, padx=10, pady=10)
    except TclError as e:
        print(f'Could not load login image: {e}')

    form_frame = Frame(frame, bg='white')
    form_frame.grid(row=0, column=1, padx=20)

    make_label(form_frame, 'Employee ID').grid(row=0, column=0, pady=5, sticky='w')
    employee_id_entry = make_entry(form_frame, width=20)
    employee_id_entry.grid(row=1, column=0, pady=5)

    make_label(form_frame, 'Password').grid(row=2, column=0, pady=5, sticky='w')
    password_entry = make_entry(form_frame, width=20, show='*')
    password_entry.grid(row=3, column=0, pady=5)

    # Eye button: show / hide the password
    login_window.eye_open = PhotoImage(file='assets/open_eye.png')
    login_window.eye_closed = PhotoImage(file='assets/close_eye.png')

    def toggle_password():
        if password_entry.cget('show') == '*':
            password_entry.config(show='')
            eye_button.config(image=login_window.eye_open)
        else:
            password_entry.config(show='*')
            eye_button.config(image=login_window.eye_closed)

    eye_button = make_button(form_frame, image=login_window.eye_closed, bg='white', hover='#e5e7eb',
                             padx=4, pady=4, command=toggle_password)
    eye_button.grid(row=3, column=1, padx=5)

    def submit():
        check_login(employee_id_entry.get(), password_entry.get(), login_window, result)

    make_button(form_frame, 'Login', command=submit, width=20).grid(row=4, column=0, pady=20, sticky='w')
    login_window.bind('<Return>', lambda event: submit())  # Enter key also logs in
    employee_id_entry.focus()

    login_window.mainloop()

    # The login window is closed now: open the page that matches the user type
    if result['usertype'] == 'Admin':
        create_window()
    elif result['usertype'] == 'Employee':
        employee_production_page()


if __name__ == '__main__':
    login_form()
