# easyVerein OpenID Connect example

This package showcases how to use the new easyVerein Identity Provider feature.
It's based on Python3.12 and uses `FastAPI`.

Create a venv and run:
```bash
pip3 install -r requirements.txt
```

Set the environment variables for `client_id` and `client_secret`. 
Then start the package using:

`fastapi dev main.py`

Navigate with your browser to `http://localhost:8000/oauth/providers` and login using easyVerein :)