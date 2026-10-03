"""Shared look-and-feel helpers for the whole app.

Why this file exists:
On macOS (especially in Dark Mode) plain tkinter widgets ignore some colours:
  * Button ignores bg, so white text ends up on a light button (invisible).
  * Label / Entry / Radiobutton use white text in Dark Mode, so they vanish on a white page.
The helpers below always set the colours explicitly, so the app looks the same everywhere.
"""
from tkinter import *
from tkinter import ttk

# Colours used across the app
BLUE = '#0F4D7D'
TEXT = '#1f2937'
ENTRY_BG = 'lightyellow'
BORDER = '#9ca3af'
FONT = 'Helvetica'


def center_window(window, width, height):
    """Place the window in the middle of the screen."""
    x = int((window.winfo_screenwidth() - width) / 2)
    y = int((window.winfo_screenheight() - height) / 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def setup_theme(window):
    """Call once after creating Tk(). Gives tables, dropdowns and radio buttons a readable light theme."""
    style = ttk.Style(window)
    style.theme_use('clam')  # the 'clam' theme respects our colours on every OS

    # Tables
    style.configure('Treeview', background='white', foreground='black', fieldbackground='white',
                    font=(FONT, 11), rowheight=26, borderwidth=0)
    style.map('Treeview', background=[('selected', '#cfe3f5')], foreground=[('selected', 'black')])
    style.configure('Treeview.Heading', background=BLUE, foreground='white',
                    font=(FONT, 11, 'bold'), relief='flat')
    style.map('Treeview.Heading', background=[('active', '#0b3a5f')])

    # Dropdowns (also used by the date picker)
    for name in ('TCombobox', 'DateEntry'):
        style.configure(name, fieldbackground='white', background='#e5e7eb', foreground='black',
                        arrowcolor=BLUE, selectbackground='white', selectforeground='black')
        style.map(name, fieldbackground=[('readonly', 'white')], foreground=[('readonly', 'black')],
                  selectbackground=[('readonly', 'white')], selectforeground=[('readonly', 'black')])
    window.option_add('*TCombobox*Listbox.background', 'white')
    window.option_add('*TCombobox*Listbox.foreground', 'black')
    window.option_add('*TCombobox*Listbox.selectBackground', '#cfe3f5')
    window.option_add('*TCombobox*Listbox.selectForeground', 'black')

    # Radio buttons (Sales filter)
    style.configure('Light.TRadiobutton', background='white', foreground=TEXT, font=(FONT, 12))
    style.map('Light.TRadiobutton', background=[('active', 'white')])


def make_label(parent, text='', font=(FONT, 14), bg='white', fg=TEXT, **options):
    """A label with a fixed text colour (so it never turns white in Dark Mode)."""
    return Label(parent, text=text, font=font, bg=bg, fg=fg, **options)


def make_entry(parent, font=(FONT, 14), width=None, show=None, bg=ENTRY_BG):
    """A text box with fixed colours and a thin border."""
    options = dict(font=font, bg=bg, fg='black', insertbackground='black', relief=FLAT,
                   highlightthickness=1, highlightbackground=BORDER, highlightcolor=BLUE)
    if width is not None:
        options['width'] = width
    if show is not None:
        options['show'] = show
    return Entry(parent, **options)


def make_text(parent, width=25, height=4, font=(FONT, 12), bg=ENTRY_BG):
    """A multi-line text box with fixed colours."""
    return Text(parent, width=width, height=height, font=font, bg=bg, fg='black',
                insertbackground='black', relief=FLAT, wrap=WORD,
                highlightthickness=1, highlightbackground=BORDER, highlightcolor=BLUE)


def _darker(widget, color, factor=0.85):
    """Return a slightly darker version of a colour (used for the hover effect)."""
    red, green, blue = [value // 256 for value in widget.winfo_rgb(color)]
    return '#%02x%02x%02x' % (int(red * factor), int(green * factor), int(blue * factor))


def make_button(parent, text='', command=None, image=None, bg=BLUE, fg='white',
                font=(FONT, 14), width=None, anchor='center', padx=10, pady=5, hover=None):
    """A clickable button that shows the same colours on macOS, Windows and Linux.

    It is a Label that reacts to clicks, because the real tkinter Button ignores
    background colours on macOS. Use it like Button: .grid() / .pack() / .place().
    """
    options = dict(text=text, bg=bg, fg=fg, font=font, anchor=anchor, padx=padx, pady=pady, cursor='hand2')
    if image is not None:
        options['image'] = image
        options['compound'] = LEFT
    if width is not None:
        options['width'] = width
    button = Label(parent, **options)

    hover_color = hover or _darker(button, bg)
    button.bind('<Enter>', lambda event: button.config(bg=hover_color))
    button.bind('<Leave>', lambda event: button.config(bg=bg))

    def on_release(event):
        # Only run the command if the mouse is still over the button when released
        inside = 0 <= event.x <= button.winfo_width() and 0 <= event.y <= button.winfo_height()
        if inside and command is not None:
            command()

    button.bind('<ButtonRelease-1>', on_release)
    return button


def make_radio(parent, text, variable, value, command):
    """A radio button with readable text."""
    return ttk.Radiobutton(parent, text=text, variable=variable, value=value,
                           command=command, style='Light.TRadiobutton')


def create_treeview(parent, columns, headings, widths, anchors=None):
    """Create a table with both scrollbars inside `parent` and return it."""
    scroll_y = Scrollbar(parent, orient=VERTICAL)
    scroll_x = Scrollbar(parent, orient=HORIZONTAL)
    tree = ttk.Treeview(parent, columns=columns, show='headings', selectmode='browse',
                        yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    scroll_y.pack(side=RIGHT, fill=Y)
    scroll_x.pack(side=BOTTOM, fill=X)
    scroll_y.config(command=tree.yview)
    scroll_x.config(command=tree.xview)
    tree.pack(fill=BOTH, expand=1)

    for index, column in enumerate(columns):
        tree.heading(column, text=headings[index])
        anchor = anchors[index] if anchors else 'center'
        tree.column(column, width=widths[index], anchor=anchor)
    return tree


def fill_treeview(tree, records):
    """Remove all rows from the table and show `records` instead."""
    tree.delete(*tree.get_children())
    for record in records:
        tree.insert('', END, values=record)


def selected_id(tree):
    """Return the id (first column) of the selected row, or None if nothing is selected."""
    selection = tree.selection()
    if not selection:
        return None
    return tree.item(selection[0])['values'][0]


def fmt_number(value):
    """Show 5.000 as 5 and 2.500 as 2.5 (for quantities)."""
    return f'{float(value):.3f}'.rstrip('0').rstrip('.')
