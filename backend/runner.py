import subprocess

def run_script(script):
    try:
        result = subprocess.run(['python', script], capture_output=True, text=True, check=True)
        print(f"--- SUCCESS: {script} ---")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"--- ERROR: {script} ---")
        print(e.stderr)
        print(e.stdout)

run_script('IntegratedPostGreSQL.py')
run_script('FeatureEngineering.py')
