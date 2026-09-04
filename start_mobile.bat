@echo off
title HARNESS // Expo Mobile Companion
echo ========================================================
echo   HARNESS EXECUTIVE OS - EXPO MOBILE COMPANION
echo   1. Open Expo Go on your iPhone (Free from App Store)
echo   2. Scan the QR code below with your iPhone Camera
echo ========================================================
cd client
npx expo start --tunnel
pause
