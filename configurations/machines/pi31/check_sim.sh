#!/bin/bash
docker ps --format '{{.Names}}' | grep -Eq "^sim-rincage$"