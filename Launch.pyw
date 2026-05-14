import runpy, os, sys
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
sys.path.insert(0, app_dir)
os.chdir(app_dir)
runpy.run_path(os.path.join(app_dir, "main.py"), run_name="__main__")
