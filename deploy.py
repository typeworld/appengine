import os
import sys
import time
import typeworld
from subprocess import Popen, PIPE, STDOUT

# List of commands as tuples of:
# - Description
# - Actual command
# - True if this command is essential to the build process (must exit with 0), otherwise False

version = time.strftime("%Y%m%dt%H%M%S", time.gmtime())
url = f"https://{version}-dot-typeworld2.appspot.com"


testPath = os.path.join(os.path.dirname(typeworld.__file__))

print(sys.version)
print(url)

commands = (
    ("Syntax checking", "python3 -m py_compile typeworldserver/__init__.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/api.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/billing_stripe.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/blog.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/classes.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/definitions.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/developer.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/helpers.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/hypertext.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/mq.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/translations.py", True),
    ("Syntax checking", "python3 -m py_compile typeworldserver/web.py", True),
    ("Testing NDB function", "python3 test_ndb.py", True),
    (
        "Deploying Google App Engine",
        f"gcloud app deploy --quiet --project typeworld2 --version {version} --no-promote",
        True,
    ),
    (f"Testing server function at {url}", f"python3 test.py {url}", True),
    (f"Testing API at {url}", f"python3 {testPath}/test.py {url}", True),
    (
        f"Moving traffic to {version}",
        f"gcloud app services set-traffic default --splits {version}=1 --quiet",
        True,
    ),
)


for description, command, mustSucceed in commands:

    # Print which step we’re currently in
    print(description, "...")

    # Execute the command, fetch both its output as well as its exit code
    out = Popen(command, stderr=STDOUT, stdout=PIPE, shell=True)
    output, exitcode = out.communicate()[0].decode(), out.returncode

    # If the exit code is not zero and this step is marked as necessary to succeed,
    # print the output and quit the script.
    if exitcode != 0 and mustSucceed:
        print(output)
        print()
        print(command)
        print()
        print('Step "%s" failed! See above.' % description)
        print("Command used: %s" % command)
        print()
        sys.exit(666)


print("Finished successfully.")
print()
