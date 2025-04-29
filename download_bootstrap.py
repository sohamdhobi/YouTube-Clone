import os
import requests

# Create the directory if it doesn't exist
os.makedirs('static/js', exist_ok=True)

# Download the file
url = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
response = requests.get(url)

# Save the file
with open('static/js/bootstrap.bundle.min.js', 'wb') as f:
    f.write(response.content)

print('Bootstrap bundle downloaded successfully!') 