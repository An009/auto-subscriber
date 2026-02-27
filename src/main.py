import sys

def main():
    try:
        from .gui import run_gui
        run_gui()
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Did you install dependencies with 'pip install -r requirements.txt'?")
        sys.exit(1)

if __name__ == "__main__":
    main()
