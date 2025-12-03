"""
Launcher for Subtitle Transcriber PRO
Allows users to choose between CustomTkinter and PyQt5 GUIs
"""
import sys


def show_gui_selector():
    """Show a simple dialog to select GUI framework."""
    print("=" * 60)
    print("  Subtitle Transcriber PRO - GUI Selector")
    print("=" * 60)
    print()
    print("Choose your preferred interface:")
    print()
    print("  1. PyQt5 (Recommended) - Modern, professional UI")
    print("  2. CustomTkinter - Original UI")
    print()
    print("=" * 60)
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        
        if choice == "1":
            return "pyqt5"
        elif choice == "2":
            return "customtkinter"
        else:
            print("Invalid choice. Please enter 1 or 2.")


def launch_pyqt5():
    """Launch the PyQt5 GUI."""
    try:
        from gui_pyqt5 import run_app
        print("Starting PyQt5 GUI...")
        run_app()
    except ImportError as e:
        print("\n" + "=" * 60)
        print("ERROR: PyQt5 is not installed!")
        print("=" * 60)
        print("\nTo install PyQt5, run:")
        print("  pip install PyQt5")
        print("\nOr install all requirements:")
        print("  pip install -r requirements.txt")
        print()
        sys.exit(1)


def launch_customtkinter():
    """Launch the CustomTkinter GUI."""
    try:
        from gui import TranscriptionApp
        print("Starting CustomTkinter GUI...")
        app = TranscriptionApp()
        app.mainloop()
    except ImportError as e:
        print("\n" + "=" * 60)
        print("ERROR: CustomTkinter is not installed!")
        print("=" * 60)
        print("\nTo install CustomTkinter, run:")
        print("  pip install customtkinter")
        print("\nOr install all requirements:")
        print("  pip install -r requirements.txt")
        print()
        sys.exit(1)


def main():
    """Main launcher function."""
    # Check if GUI choice was provided as command-line argument
    if len(sys.argv) > 1:
        choice = sys.argv[1].lower()
        if choice in ["pyqt5", "pyqt", "qt", "1"]:
            launch_pyqt5()
        elif choice in ["customtkinter", "tkinter", "ctk", "2"]:
            launch_customtkinter()
        else:
            print(f"Unknown GUI choice: {choice}")
            print("Valid options: pyqt5, customtkinter")
            sys.exit(1)
    else:
        # Interactive selection
        choice = show_gui_selector()
        if choice == "pyqt5":
            launch_pyqt5()
        else:
            launch_customtkinter()


if __name__ == "__main__":
    main()

