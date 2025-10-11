# Config as a Service (CAS) - Main package
import os
import sys

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.curdir, 'cas'))
print(project_root)
sys.path.append(project_root)