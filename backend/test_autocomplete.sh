#!/bin/bash

# Test script for Mountain Project autocomplete endpoint
# Usage: ./test_autocomplete.sh [search_query] [limit]
#
# Examples:
#   ./test_autocomplete.sh "red"
#   ./test_autocomplete.sh "bishop" 3
#   ./test_autocomplete.sh "usa"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
BASE_URL="http://localhost:8000"
SEARCH_QUERY="${1:-red}"
LIMIT="${2:-10}"

echo -e "${YELLOW}Mountain Project Autocomplete Endpoint Test${NC}"
echo "=============================================="
echo ""

# Step 1: Get JWT token
echo -e "${YELLOW}Step 1: Logging in to get JWT token...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test3@test.com",
    "password": "testpass123"
  }')

# Extract access token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}Failed to get access token. Login response:${NC}"
    echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"
    echo ""
    echo -e "${YELLOW}Note: Update the email/password in this script to match your user credentials${NC}"
    exit 1
fi

echo -e "${GREEN}Login successful! Token obtained.${NC}"
echo ""

# Step 2: Test autocomplete endpoint
echo -e "${YELLOW}Step 2: Testing autocomplete endpoint...${NC}"
echo "Query: '$SEARCH_QUERY'"
echo "Limit: $LIMIT"
echo ""

AUTOCOMPLETE_URL="${BASE_URL}/api/destinations/autocomplete/?q=${SEARCH_QUERY}&limit=${LIMIT}"

echo -e "${YELLOW}Request URL:${NC}"
echo "$AUTOCOMPLETE_URL"
echo ""

AUTOCOMPLETE_RESPONSE=$(curl -s -X GET "$AUTOCOMPLETE_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo -e "${GREEN}Response:${NC}"
echo "$AUTOCOMPLETE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$AUTOCOMPLETE_RESPONSE"
echo ""

# Count results
RESULT_COUNT=$(echo "$AUTOCOMPLETE_RESPONSE" | grep -o '"slug"' | wc -l | tr -d ' ')

if [ "$RESULT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}Success! Found $RESULT_COUNT destination(s)${NC}"
else
    echo -e "${YELLOW}No destinations found for query: '$SEARCH_QUERY'${NC}"
fi

echo ""
echo "=============================================="
echo -e "${GREEN}Test complete!${NC}"
echo ""
echo "Try other queries:"
echo "  ./test_autocomplete.sh \"bishop\""
echo "  ./test_autocomplete.sh \"usa\""
echo "  ./test_autocomplete.sh \"kentucky\""
