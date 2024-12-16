import os
from typing import Annotated

import requests
from fastapi import FastAPI, Form, status
from uuid import uuid4
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi import Request
from fastapi.templating import Jinja2Templates
import random
import string
import base64
import hashlib

templates = Jinja2Templates(directory="templates")
app = FastAPI()

client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
authorization_path = "/oauth2/authorize/"
base_uri = "https://easyverein.com"
# base_uri = "http://localhost:8000"
access_token_path = "/oauth2/token/"
code_verifier = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(43, 128)))
scopes = ['openid', 'myself', "profile"]

prefix = os.getenv("prefix_oidc", "http://")

states = {"default": {
    "client_id": client_id,
    "client_secret": client_secret,
    "url": base_uri,
    "scopes": scopes
}}


def get_redirect_url(request: Request) -> str:
    base = str(request.base_url)
    base = base.split("://")[1]
    base = prefix + base
    return base + "oauth/callback/easyVerein"


def get_post_logout_redirect_url(request: Request) -> str:
    base = str(request.base_url)
    base = base.split("://")[1]
    base = prefix + base
    return base + "oauth/adios/easyVerein"


@app.get("/")
def index(request: Request):
    """
    This is the index page
    :param request:
    :return:
    """
    state_redirect_uri = get_redirect_url(request)
    post_logout_redirect_uri = get_post_logout_redirect_url(request)

    return templates.TemplateResponse("index.html", {"request": request, "ruri": state_redirect_uri,
                                                     "luri": post_logout_redirect_uri})


@app.post("/acquire")
def acquire(request: Request, client_id: Annotated[str, Form()], client_secret: Annotated[str, Form()],
            url: Annotated[str, Form()], scopes: Annotated[str, Form()]):
    """
    This prepares the state and redirects to the select provider page
    :param request:
    :param content:
    :param scopes:
    :return:
    """
    state = str(uuid4())
    states[state] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "url": url,
        "scopes": scopes.split(" ")
    }
    return RedirectResponse(f"/oauth/providers?state={state}", status_code=status.HTTP_303_SEE_OTHER)


@app.get('/oauth/providers')
def get_providers(request: Request, state: str = "default"):
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').replace('=', '')
    if not state in states:
        return Response("Invalid state", status_code=400)
    state_client_id = states[state]["client_id"]
    state_base_uri = states[state]["url"]
    state_redirect_uri = get_redirect_url(request)
    state_scopes = states[state]["scopes"]

    # get the authorization url
    easyVerein_auth_url = f"{state_base_uri}{authorization_path}?response_type=code&code_challenge={code_challenge}&code_challenge_method=S256&client_id={state_client_id}&redirect_uri={state_redirect_uri}&scope={"%20".join(state_scopes)}&state={state}"

    return templates.TemplateResponse("providers.html",
                                      {"request": request, "easyVerein_auth_url": easyVerein_auth_url})


@app.get("/button")
def get_button(request: Request):
    return templates.TemplateResponse("sign_in_with_easyVerein_btn.html", {"request": request})


@app.get('/oauth/callback/easyVerein')
def get_response_from_stack_exchange(request: Request, code: str = "", error: str = "", state: str = "default"):
    if error:
        return HTMLResponse(f"""
        <body>
           <h1>Rejected</h1>
           <p>{error}</p>
        </body>
        
        """)
    if not state in states:
        return Response("Invalid state", status_code=400)

    state_client_id = states[state]["client_id"]
    state_client_secret = states[state]["client_secret"]
    state_base_uri = states[state]["url"]
    state_redirect_uri = get_redirect_url(request)

    code_exchange_data = {"client_id": state_client_id, "client_secret": state_client_secret, "code": code,
                          "code_verifier": code_verifier, "redirect_uri": state_redirect_uri,
                          "grant_type": "authorization_code"}

    if not (
            "localhost" in state_base_uri or "127.0.0.1" in state_base_uri or "0.0.0.0" in state_base_uri) and "localhost" in state_redirect_uri:
        return HTMLResponse(""
                            "<h1>Localhost testing</h1>"
                            "It is impossible for the test client to perform the following request, because the test client cant access the server url per POST<br>"
                            ""
                            "Use Thunderclient or another tool to perform the following post request:<br>"
                            f"POST <br>"
                            f"<code>{state_base_uri}{access_token_path}<br>"
                            f"data: {code_exchange_data}<br></code>"
                            ""
                            "Or use the following curl command:<br>"
                            f"<code>curl -X POST {state_base_uri}{access_token_path} -d {code_exchange_data}</code><br>"

                            "")

    resp = requests.post(f"{state_base_uri}{access_token_path}", data=code_exchange_data)
    if resp.status_code < 400:
        print(resp.text)
        resp_json = resp.json()
    else:
        return HTMLResponse(resp.content.decode("utf-8"))

    access_token = resp_json["access_token"]
    user_name = "Unknown :("
    if ("localhost" in state_base_uri or "127.0.0.1" in state_base_uri) or not (
            "localhost" in state_redirect_uri or "127.0.0.1" in state_redirect_uri or "0.0.0.0" in state_redirect_uri):
        user_response = requests.get(f"{state_base_uri}/api/latest/member/me", headers={
            "Authorization": f"Bearer {access_token}"
        })

        cd_response = requests.get(f"{state_base_uri}/api/latest/contact-details/me", headers={
            "Authorization": f"Bearer {access_token}"
        })

        if cd_response.status_code == 200:
            cd_data = cd_response.json()
            print(cd_data)

        if user_response.status_code == 200:
            user_data = user_response.json()
            user_name = user_data["emailOrUserName"]

        oidc_user_info_request = requests.get(f"{state_base_uri}/oauth2/userinfo/", headers={
            "Authorization": f"Bearer {access_token}"
        })

        print("The OIDC id token contains the following content:", oidc_user_info_request.text)

    post_logout_redirect_uri = get_post_logout_redirect_url(request)

    rp_logout_url = f"{state_base_uri}/oauth2/logout?client_id={state_client_id}&post_logout_redirect_uri={post_logout_redirect_uri}"
    if "id_token" in resp_json:
        rp_logout_url += f"&id_token_hint={resp_json.get('id_token')}"
    html_content = f"""
    <html>
        <head>
            <title>Connected to EasyVerein</title>
        </head>
        <body>
            <h3>Success! {user_name}</h3>
            <p>We've successfully obtained your easyVerein access token!</p>
            <p>{resp_json}</p>
            <p>Verify ID Token <a href="https://jwt.io/">here</a></p>
            <p>Revoke token: <a href="/oauth/revoke?access_token={access_token}">here</a></p>
            <br/>
            <br/>
            <p>RP-Logout: <a href="{rp_logout_url}">Initiate</a></p>
        </body>
    </html>
    """
    return HTMLResponse(html_content)


@app.get("/oauth/revoke")
def revoke_token(request: Request, access_token: str, state: str = "default"):
    state_client_id = states[state]["client_id"]
    state_client_secret = states[state]["client_secret"]
    state_base_uri = states[state]["url"]

    response = requests.post(f"{state_base_uri}/oauth2/revoke_token/",
                             data=f"token={access_token}&client_id={state_client_id}&client_secret={state_client_secret}",
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    print(response)
    if response.status_code == 200:
        return HTMLResponse(
            f"""
            <p>successful</p>
            <a href="/oauth/providers?state={state}">Go back</a>
            """
        )
    else:
        return HTMLResponse("error")


@app.get("/oauth/adios/easyVerein")
def adios(request: Request):
    return HTMLResponse("Successful!")
