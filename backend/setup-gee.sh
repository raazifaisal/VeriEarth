#!/bin/bash

# Setup script for Google Earth Engine authentication in containers

echo "🚀 Setting up Google Earth Engine for VeriEarth..."

# Check if GEE_SERVICE_ACCOUNT_KEY is set
if [ -z "$GEE_SERVICE_ACCOUNT_KEY" ]; then
    echo "❌ GEE_SERVICE_ACCOUNT_KEY environment variable not set"
    echo ""
    echo "To set it up:"
    echo "1. Go to https://console.cloud.google.com/"
    echo "2. Create/select a project"
    echo "3. Enable 'Google Earth Engine API'"
    echo "4. Go to 'IAM & Admin' → 'Service Accounts'"
    echo "5. Create a new service account"
    echo "6. Download the JSON key file"
    echo "7. Set the environment variable:"
    echo "   export GEE_SERVICE_ACCOUNT_KEY='$(cat your-service-account-key.json)'"
    echo ""
    echo "Then restart your containers:"
    echo "   docker-compose down && docker-compose up -d"
    exit 1
fi

echo "✅ GEE_SERVICE_ACCOUNT_KEY is set"
echo "🔄 Restarting containers to apply changes..."

docker-compose down
docker-compose up -d

echo "✅ Setup complete! Test the connection with:"
echo "   curl -X GET http://localhost:8000/api/supply-chain/test-eo"
