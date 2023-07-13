from msal import PublicClientApplication
import time
import requests
import json


def getxbl3(access_token):
    #XBOX LIVE TOKEN ------------------------------------------------------------------------------------------------------------------------------
    def send_xbox_auth_request(access_token):
        # Prepare the payload
        payload = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={access_token}"
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }

        # Send the POST request
        url = "https://user.auth.xboxlive.com/user/authenticate"
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers)

        # Process the response
        if response.status_code == 200:
            # Request successful
            formatted_response = json.dumps(response.json(), indent=4)
            return formatted_response
        else:
            # Request failed
            print("Request failed!")
            print("Status Code:", response.status_code)
            print("Error Message:", response.text)
            return None


    formatted_response = send_xbox_auth_request(access_token)
    data = json.loads(formatted_response)
    token = data["Token"]
    uhs = data["DisplayClaims"]["xui"][0]["uhs"]


    #XTXS TOKEN ----------------------------------------------------------------------------------------
    def send_xsts_authorize_request(xbl_token):
        # Prepare the payload
        payload = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [
                    xbl_token
                ]
            },
            "RelyingParty": "https://pocket.realms.minecraft.net/",
            "TokenType": "JWT"
        }

        # Send the POST request
        url = "https://xsts.auth.xboxlive.com/xsts/authorize"
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers)

        # Process the response
        if response.status_code == 200:
            # Request successful
            formatted_response = json.dumps(response.json(), indent=4)
            return formatted_response
        else:
            # Request failed
            print("Request failed!")
            print("Status Code:", response.status_code)
            print("Error Message:", response.text)
            return None


    formatted_response = send_xsts_authorize_request(token)
    data = json.loads(formatted_response)
    token = data["Token"]
    uhs = data["DisplayClaims"]["xui"][0]["uhs"]

    xbl3token = f"XBL3.0 x={uhs};{token}"
    return xbl3token

def refreshtoken(user_id, conn, c):
    client_id = "e3224e84-2c6c-44c4-916a-4b877c4cb33c" #ur client id
    scopes = ["XboxLive.signin"]
    authority = "https://login.microsoftonline.com/consumers"

    pca = PublicClientApplication(client_id, authority=authority)

    # Retrieve the access_token and refresh_token from the database using user_id
    c.execute("SELECT refresh_token FROM link_data WHERE user_id = ?", (user_id,))
    result = c.fetchone()

    if result is not None:
        refresh_token = result[0]

        # Acquire a new access token using the refresh token
        result = pca.acquire_token_by_refresh_token(refresh_token, scopes=scopes)

        if "access_token" in result:
            new_access_token = result["access_token"]
            new_refresh_token = result["refresh_token"]
            
            newxbl3token = getxbl3(new_access_token)

            # Update the access_token and refresh_token in the database
            c.execute("UPDATE link_data SET access_token = ?, refresh_token = ?, xbl3token = ? WHERE user_id = ?", (new_access_token, new_refresh_token, newxbl3token, user_id))
            conn.commit()  # Commit the changes
        else:
            print("An error occurred while refreshing the token.")
    else:
        print("User ID not found in the database.")
    
    conn.commit()
