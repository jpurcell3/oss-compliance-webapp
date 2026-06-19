@echo off
REM Docker helper script for OSS Compliance Web Application (Windows)

set IMAGE_NAME=oss-compliance-webapp
set REGISTRY=ghcr.io/jpurcell3/oss-scanner
set VERSION=%1
if "%VERSION%"=="" set VERSION=latest

echo OSS Compliance Web Application - Docker Helper Script
echo ======================================================

if "%2"=="" goto help

if "%1"=="build" goto build
if "%1"=="run" goto run
if "%1"=="stop" goto stop
if "%1"=="login-ghcr" goto login_ghcr
if "%1"=="tag-ghcr" goto tag_ghcr
if "%1"=="push-ghcr" goto push_ghcr
if "%1"=="pull-ghcr" goto pull_ghcr
if "%1"=="logs" goto logs
if "%1"=="cleanup" goto cleanup
if "%1"=="help" goto help
goto unknown

:build
echo Building Docker image...
docker build -t %IMAGE_NAME%:%VERSION% .
echo ✅ Image built: %IMAGE_NAME%:%VERSION%
goto end

:run
echo Running container...
docker run -d -p 5001:5001 -e ENCRYPTION_KEY=%ENCRYPTION_KEY% -e DEBUG_LOGGING=true -v %cd%/config:/app/config -v %cd%/reports:/app/reports -v %cd%/uploads:/app/uploads -v %cd%/cache:/app/cache -v %cd%/instance:/app/instance --name %IMAGE_NAME% %IMAGE_NAME%:%VERSION%
echo ✅ Container started: %IMAGE_NAME%
echo 🌐 Access at: http://localhost:5001
echo ℹ️  Add tokens via web UI at http://localhost:5001/config
goto end

:stop
echo Stopping container...
docker stop %IMAGE_NAME% 2>nul
docker rm %IMAGE_NAME% 2>nul
echo ✅ Container stopped and removed
goto end

:login_ghcr
echo Logging in to GitHub Container Registry...
echo Enter your GitHub username:
set /p GITHUB_USER
echo Enter your GitHub personal access token:
set /p GITHUB_TOKEN
echo %GITHUB_TOKEN% | docker login ghcr.io -u %GITHUB_USER% --password-stdin
echo ✅ Logged in to ghcr.io
goto end

:tag-ghcr
echo Tagging image for GitHub Container Registry...
docker tag %IMAGE_NAME%:%VERSION% %REGISTRY%:%VERSION%
echo ✅ Tagged: %REGISTRY%:%VERSION%
goto end

:push-ghcr
echo Pushing to GitHub Container Registry...
docker push %REGISTRY%:%VERSION%
echo ✅ Pushed: %REGISTRY%:%VERSION%
goto end

:pull-ghcr
echo Pulling from GitHub Container Registry...
docker pull %REGISTRY%:%VERSION%
echo ✅ Pulled: %REGISTRY%:%VERSION%
goto end

:logs
echo Showing container logs...
docker logs -f %IMAGE_NAME%
goto end

:cleanup
echo Cleaning up Docker resources...
docker system prune -f
echo ✅ Cleanup complete
goto end

:help
echo Usage: docker-helper.bat [command] [version]
echo.
echo Commands:
echo   build       - Build Docker image
echo   run         - Run container
echo   stop        - Stop and remove container
echo   login-ghcr  - Login to GitHub Container Registry
echo   tag-ghcr    - Tag image for GitHub Container Registry
echo   push-ghcr   - Push to GitHub Container Registry
echo   pull-ghcr   - Pull from GitHub Container Registry
echo   logs        - Show container logs
echo   cleanup     - Clean up Docker resources
echo   help        - Show this help message
echo.
echo Examples:
echo   docker-helper.bat build
echo   docker-helper.bat build v1.0
echo   docker-helper.bat run
echo   docker-helper.bat tag-ghcr v1.0
echo   docker-helper.bat push-ghcr v1.0
goto end

:unknown
echo Unknown command: %1
goto help

:end