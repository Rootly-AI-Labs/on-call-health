import urllib.request
import os

url = "https://ml.globenewswire.com/Resource/Download/84c2c8ad-8f24-4119-814e-36342936302d"
output_path = "public/images/rootly-logo-official.png"

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Download the file
urllib.request.urlretrieve(url, output_path)
print(f"Downloaded Rootly logo to {output_path}")