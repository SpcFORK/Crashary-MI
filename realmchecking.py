import requests

def getinfofromcode(realmcode, xbl3token):
    url = f"https://pocket.realms.minecraft.net/worlds/v1/link/{realmcode}"

    payload = {}
    headers = {
        'Accept': '*/*',
        'authorization': f'{xbl3token}',
        'client-version': '1.20.0',
        'client-ref': '08bdb049f310d03aeabda3748f857640eb62a733',
        'user-agent': 'MCPE/UWP',
        'Accept-Language': 'en-GB,en',
        'Accept-Encoding': 'gzip, deflate, be',
        'Host': 'pocket.realms.minecraft.net'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
  
    print(response)
    realminfo = response.json()
    raw_data = response.text

    if response.status_code == 403:
        return False
    else:
        return realminfo


def checkowner(realmid, xbl3token):
    url = f"https://pocket.realms.minecraft.net/world/{realmid}/content/"

    payload = {}
    headers = {
        'client-version': '1.20.0',
        'client-ref': '08bdb049f310d03aeabda3748f857640eb62a733',
        'User-Agent': 'MCPE/UWP',
        'Authorization': f'{xbl3token}',
        'Accept': '*/*',
        'Cache-Control': 'no-cache',
        'Host': 'pocket.realms.minecraft.net',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 200:
        return True
    else:
        return False

    

    