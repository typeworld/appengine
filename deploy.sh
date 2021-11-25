# Fail fast
set -e

# gcloud config
echo "Setting gcloud configuration..."
gcloud config configurations activate default

# URL
export TEST_MOTHERSHIP="https://`date +"%Y%m%dt%H%M%S"`-dot-typeworld2.appspot.com"
VERSION=`date +"%Y%m%dt%H%M%S"`
echo $TEST_MOTHERSHIP

echo "Syntax check..."
for filename in typeworldserver/*.py; do
    echo "Python Syntax Check on" $filename
    python3 -m py_compile $filename;
done

echo "Uploading..."
gcloud app deploy --quiet --project typeworld2 --version $VERSION --no-promote

echo "PyTest..."
pytest -s

echo "Migrating traffic..."
gcloud app services set-traffic default --splits $VERSION=1 --quiet
