@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0bootstrap-docker.ps1" %*
