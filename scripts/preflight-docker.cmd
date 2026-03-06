@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0preflight-docker.ps1" %*
