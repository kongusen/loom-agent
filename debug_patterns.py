import sys
import os
sys.path.insert(0, os.getcwd())

from loom.patterns.composition import Group, Router
import inspect

print(f"Group file: {inspect.getfile(Group)}")
print(f"Group init signature: {inspect.signature(Group.__init__)}")

print(f"Router file: {inspect.getfile(Router)}")
try:
    print(f"Router init signature: {inspect.signature(Router.__init__)}")
except Exception as e:
    print(f"Router init signature error: {e}")

try:
    g = Group(steps={})
    print("Group instantiation success")
except Exception as e:
    print(f"Group instantiation failed: {e}")
