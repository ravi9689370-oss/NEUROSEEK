#!/bin/bash
# Build script for NeuroSeek AI Android APK
# Run this after setting up the project

set -e

echo "🚀 Building NeuroSeek AI Android APK..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check dependencies
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ $1 found${NC}"
    return 0
}

echo -e "${YELLOW}📋 Checking dependencies...${NC}"
check_command node
check_command npm
check_command java
check_command gradle || echo "Gradle wrapper will be used"

# Build frontend
echo -e "${YELLOW}🔨 Building frontend...${NC}"
cd frontend
npm ci
npm run build
cd ..

# Sync with Capacitor
echo -e "${YELLOW}🔄 Syncing with Capacitor...${NC}"
cd frontend
npx cap sync android
cd ..

# Build Android APK
echo -e "${YELLOW}📱 Building Android APK...${NC}"
cd frontend/android
./gradlew assembleDebug

# Find the APK
APK_PATH=$(find . -name "*.apk" -path "*/debug/*" | head -1)
if [ -n "$APK_PATH" ]; then
    echo -e "${GREEN}✅ APK built successfully!${NC}"
    echo -e "${GREEN}📦 APK location: $APK_PATH${NC}"
    
    # Copy to root for easy access
    cp "$APK_PATH" "../../neuroseek-ai-debug.apk"
    echo -e "${GREEN}📋 Copied to project root as neuroseek-ai-debug.apk${NC}"
else
    echo -e "${RED}❌ APK not found${NC}"
    exit 1
fi

cd ../..

echo -e "${GREEN}🎉 Build complete!${NC}"
echo -e "${YELLOW}📱 Install on your phone:${NC}"
echo -e "   adb install neuroseek-ai-debug.apk"
echo -e "   Or transfer the APK file to your phone and install manually"