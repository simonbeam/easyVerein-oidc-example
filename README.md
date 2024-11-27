# easyVerein OpenID Connect example

This package showcases how to use the new easyVerein Identity Provider feature.
It's based on Python3.12 and uses `FastAPI`.

Create a venv and run:
```bash
pip3 install -r requirements.txt
```

Set the environment variables for `client_id` and `client_secret`. 
Then start the package using:

```
fastapi dev main.py --port 8090
```

Navigate with your browser to `http://localhost:8090/oauth/providers` and login using easyVerein :)

### Hint:

The CORS settings of easyVerein require the client to be accessable with HTTPS. This is currently not enforced in Firefox, for testing purposes you can use Firefox. 
You can also use our test client on [https://oidc.tools.sd-server.de](https://oidc.tools.sd-server.de)
