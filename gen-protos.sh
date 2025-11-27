#!/bin/bash

uv run python \
	-m grpc_tools.protoc \
	--python_out=. \
	--grpc_python_out=. \
	-I ./protos \
	./protos/flotilla.proto
