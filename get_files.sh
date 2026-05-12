#!/bin/bash

paths=("/net/em-support/Krios1/" "/net/em-support/Krios2/" "/net/em-support/Krios3/" "/net/cista1/Krios4Falcon/" "/net/em-support/Glacios/")

for i in ${!paths[@]}
do
	path=${paths[$i]}
	find $path -maxdepth 4 -type f -newermt 20250101 -not -newermt 20260101 -name EpuSession.dm 2>/dev/null > scope$i
	#python3 parse_epu_session.py scope$i
done
