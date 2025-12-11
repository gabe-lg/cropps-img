@echo off

cls

IF EXIST ".setup_ok" (
    del .setup_ok
)

call .\run.cmd
