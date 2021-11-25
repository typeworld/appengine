# appengine

Run locally: `gunicorn -t 0 -b :80 typeworldserver:app`

Deploy safely: `sh deploy.sh`
Deploy unsafely: `gcloud config configurations activate default && gcloud app deploy --quiet`
Logs: `gcloud config configurations activate default && gcloud app logs tail`
Run Pytest locally (with locally running gunicorn server): `sh testlocally.py`

Upload indices: `gcloud config configurations activate default && gcloud app deploy index.yaml`
Deleting unused indices: `gcloud config configurations activate default && gcloud datastore indexes cleanup index.yaml`

# Stripe:

CLI command to forward event to the local development webhook: `stripe listen --forward-to http://0.0.0.0/stripe-webhook`


v=DMARC1; p=none; rua=mailto:dmarc@type.world
