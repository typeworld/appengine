# Fail fast
set -e

# gcloud config
echo "Setting gcloud configuration..."
gcloud config configurations activate default

# URL
export VERSION=`date +"%Y%m%dt%H%M%S"`
export TEST_MOTHERSHIP="https://$VERSION-dot-typeworld2.appspot.com"

echo $TEST_MOTHERSHIP

echo "Syntax check..."
for filename in typeworldserver/*.py; do
    echo "Python Syntax Check on" $filename
    python3 -m py_compile $filename;
done

echo "Uploading..."
gcloud app deploy --quiet --project typeworld2 --version $VERSION --no-promote

echo "API Test..."
TYPEWORLD_LIB_PATH=`python3 -c 'import typeworld, os; print(os.path.join(os.path.dirname(typeworld.__file__)))'`
python3 $TYPEWORLD_LIB_PATH/test.py $TEST_MOTHERSHIP

echo "PyTest..."
pytest -s

echo "Migrating traffic..."
gcloud app services set-traffic default --splits $VERSION=1 --quiet
