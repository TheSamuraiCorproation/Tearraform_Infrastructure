import os
import re
import json
import base64
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Pattern to match files like "hash_id_ai_output_timestamp.json"
PATTERN = re.compile(r"^[0-9a-f]+_ai_output_\d+\.json$")
# Default JENKINS_URL, override with environment variable if set
JENKINS_URL = os.environ.get("JENKINS_URL", "https://4585943c559d.ngrok-free.app")
JOB_NAME = os.environ.get("JOB_NAME", "terraform-deploy")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN", "THE_SAMURAI_TOKEN")
JENKINS_USER = os.environ.get("JENKINS_USER", "admin")
JENKINS_API_TOKEN = os.environ.get("JENKINS_API_TOKEN", "1187089acbf3d15c8f19f66b3accfd015e")

def lambda_handler(event, context):
    for rec in event["Records"]:
        key = rec["s3"]["object"]["key"]
        bucket = rec["s3"]["bucket"]["name"]
        if not PATTERN.match(key):
            print(f"Skipping file {key}: does not match pattern")
            continue

        params = urlencode({
            "token": JENKINS_TOKEN,
            "BUCKET": bucket,
            "KEY": key
        })
        url = f"{JENKINS_URL}/job/{JOB_NAME}/buildWithParameters?{params}"
        print(f"Attempting to trigger Jenkins at: {url}")

        auth = base64.b64encode(f"{JENKINS_USER}:{JENKINS_API_TOKEN}".encode()).decode()
        req = Request(url, method="POST")
        req.add_header("Authorization", f"Basic {auth}")

        try:
            with urlopen(req) as resp:
                print(f"Triggered Jenkins for {key}: {resp.status} {resp.reason}")
        except HTTPError as e:
            print(f"HTTP error triggering Jenkins for {key}: {e.code} {e.reason}")
        except URLError as e:
            print(f"URL error triggering Jenkins for {key}: {e.reason}")  # Fixed line
        except Exception as e:
            print(f"Unexpected error triggering Jenkins for {key}: {str(e)}")

    return {"status": "done"}
