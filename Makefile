#!/usr/bin/env make

# this loads $(ENV_FILE) as both makefile variables and into shell env
ENV_FILE?=.env
include $(ENV_FILE)
export $(shell sed 's/=.*//' $(ENV_FILE))

.PHONY:  deps black docs

deps:
	./dependencies.py

black:
	black docs pylicense3 tests

docs:
	make -C docs html

dist:
	python3 -m build

upload:
	twine upload dist/*

test_upload:
	twine upload --repository testpypi dist/*
