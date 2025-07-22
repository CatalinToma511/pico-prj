from updateManager import updateManager

uc = updateManager()
uc.run()

try:
    import sys
    sys.path.append("app")
    import project_app as prj # type: ignore
    prj.run()
except Exception as e:
    print(f'Error running the app: {e}')