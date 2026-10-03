"""Entry point for the Manufacturing Management System. Start the app with:  python main.py"""
import os

# Always look for the 'assets' folder next to this file, no matter where the app is started from
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from loginform import login_form

if __name__ == "__main__":
    login_form()
