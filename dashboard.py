import time
from tkinter import *
from tkinter import messagebox

from database import initialize_database, run_query, current_user
from ui import setup_theme, center_window, make_label, make_button
from employees import employee_form
from supplier import supplier_form
from materials import material_form
from products import product_form
from production import production_form

# The form (frame) that is currently open, so only one is visible at a time
current_frame = None


def show_form(form_function, window):
    """Close the open form (if any) and open the new one."""
    global current_frame
    if current_frame is not None and current_frame.winfo_exists():
        current_frame.destroy()
    current_frame = form_function(window)


def update_stats(stat_labels):
    """Refresh the six counters (one database query) and repeat every 5 seconds."""
    row = run_query(
        'SELECT (SELECT COUNT(*) FROM employee_data), (SELECT COUNT(*) FROM supplier_data), '
        '(SELECT COUNT(*) FROM material_data), (SELECT COUNT(*) FROM product_data), '
        '(SELECT COUNT(*) FROM production_data), '
        '(SELECT COUNT(*) FROM material_data WHERE quantity <= reorder_level)', fetch='one', show_errors=False)
    if row:
        for key, value in zip(('employee', 'supplier', 'material', 'product', 'production', 'low'), row):
            stat_labels[key].config(text=value)
    stat_labels['employee'].after(5000, lambda: update_stats(stat_labels))


def update_clock(subtitle_label):
    """Show the current date and time and repeat every second."""
    date_time = time.strftime('%I:%M:%S %p on %A, %B %d, %Y')
    subtitle_label.config(text=f"Welcome {current_user['name']}\t\t\t {date_time}")
    subtitle_label.after(1000, lambda: update_clock(subtitle_label))


def confirm_exit(window):
    """Ask before closing the application."""
    if messagebox.askyesno('Confirm Exit', 'Are you sure you want to exit?'):
        window.destroy()


def create_title(window):
    """Blue title bar at the top."""
    window.title_image = PhotoImage(file='assets/inventory.png')  # keep a reference
    title_label = make_label(window, '\t   Manufacturing Management System', font=('Helvetica', 32, 'bold'),
                             bg='#010c48', fg='white', image=window.title_image, compound=LEFT,
                             anchor='w', padx=20)
    title_label.place(x=0, y=0, relwidth=1)


def create_subtitle(window):
    """Grey bar under the title with the welcome text and the clock."""
    subtitle_label = make_label(window, '', font=('Helvetica', 12), bg='#4d636d', fg='white')
    subtitle_label.place(x=0, y=70, relwidth=1)
    update_clock(subtitle_label)


def create_left_menu(window):
    """Left menu with a button for every section."""
    left_frame = Frame(window, bg='white')
    left_frame.place(x=0, y=102, width=200, height=555)

    # Load the icons (keep references on the window so they are not garbage collected)
    window.menu_images = {name: PhotoImage(file=f'assets/{name}.png')
                          for name in ('logo', 'employee', 'supplier', 'category', 'product', 'sales', 'exit')}

    Label(left_frame, image=window.menu_images['logo'], bg='white').pack()
    make_label(left_frame, 'Menu', font=('Helvetica', 20, 'bold'), bg='#009688', fg='white').pack(fill=X)

    menu_items = [
        ('employee', ' Employees', lambda: show_form(employee_form, window)),
        ('supplier', ' Suppliers', lambda: show_form(supplier_form, window)),
        ('category', ' Materials', lambda: show_form(material_form, window)),
        ('product', ' Products', lambda: show_form(product_form, window)),
        ('sales', ' Production', lambda: show_form(production_form, window)),
        ('exit', ' Exit', lambda: confirm_exit(window)),
    ]
    for icon_name, text, command in menu_items:
        button = make_button(left_frame, text, command=command, image=window.menu_images[icon_name],
                             bg='white', fg='#1f2937', hover='#dbeafe', font=('Helvetica', 14, 'bold'),
                             anchor='w', padx=8, pady=6)
        button.pack(fill=X, padx=4, pady=1)


def create_stat_frame(window, x, y, bg_color, icon_file, title):
    """One coloured card with an icon, a title and a number. Returns the number label."""
    frame = Frame(window, bg=bg_color, bd=3, relief=RIDGE)
    frame.place(x=x, y=y, height=170, width=280)

    frame.icon = PhotoImage(file=f'assets/{icon_file}')  # keep a reference
    Label(frame, image=frame.icon, bg=bg_color).pack(pady=10)
    make_label(frame, title, font=('Helvetica', 15, 'bold'), bg=bg_color, fg='white').pack()
    count_label = make_label(frame, '0', font=('Helvetica', 30, 'bold'), bg=bg_color, fg='white')
    count_label.pack()
    return count_label


def create_dashboard(window):
    """Create the six statistic cards (3 x 2). Returns a dictionary with their number labels."""
    return {
        'employee': create_stat_frame(window, 230, 125, '#2C3E50', 'total_emp.png', 'Total Employees'),
        'supplier': create_stat_frame(window, 560, 125, '#8E44AD', 'total_sup.png', 'Total Suppliers'),
        'material': create_stat_frame(window, 890, 125, '#27AE60', 'total_cat.png', 'Raw Materials'),
        'product': create_stat_frame(window, 230, 330, '#2C3E50', 'total_prod.png', 'Products'),
        'production': create_stat_frame(window, 560, 330, '#2980B9', 'total_sales.png', 'Production Runs'),
        'low': create_stat_frame(window, 890, 330, '#E74C3C', 'low_stock.png', 'Low Stock Materials'),
    }


def create_window():
    """Build and run the Admin dashboard window."""
    global current_frame
    current_frame = None

    window = Tk()
    setup_theme(window)
    window.title('Dashboard')
    window.resizable(False, False)
    window.config(bg='white')
    center_window(window, 1270, 668)
    initialize_database()

    create_title(window)
    create_subtitle(window)
    create_left_menu(window)
    stat_labels = create_dashboard(window)
    update_stats(stat_labels)

    window.mainloop()


if __name__ == '__main__':
    create_window()
