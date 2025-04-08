import curl_cffi.requests as requests
from curl_cffi.curl import CurlHttpVersion
import pyotp


def login(user_id, password, totp_key):
    base_url = "https://web.stocko.in/assets/broker/app-config.json"
    login_url = "https://web.stocko.in/api/v3/user/login"
    otp_url = "https://web.stocko.in/api/v3/user/validatetotp"

    headers = {"x-device-type": "web"}

    with requests.Session(
        impersonate="safari_ios", headers=headers, http_version=CurlHttpVersion(2)
    ) as s:
        _ = s.get(base_url)
        login_response = s.post(
            login_url, data={"login_id": user_id, "password": password}
        )
        if login_response.status_code == 200:
            twofa_token = (
                login_response.json()
                .get("data", {})
                .get("twofa", {})
                .get("twofa_token")
            )

            if twofa_token:
                otp_response = s.post(
                    otp_url,
                    data={
                        "login_id": user_id,
                        "twofa_token": twofa_token,
                        "totp": pyotp.TOTP(totp_key).now(),
                    },
                )
                if otp_response.status_code == 200:
                    auth_token = otp_response.json().get("data", {}).get("auth_token")
                    print(" AUTH TOKEN ".center(150, "="))
                    print(auth_token)
                    print("*" * 150)
                else:
                    print(f"Error in otp validation :: {otp_response.text}")
        else:
            print(f"Error in login response :: {login_response.text}")

    return auth_token
