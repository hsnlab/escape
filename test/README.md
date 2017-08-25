# Testframework for testing ESCAPE

## Description

The testframework uses the standard Python's unittest library to define the 
different testcases.

Each testcase and the related files are organized into different folders with 
the prefix *case*.

The testcases cas be run with the main runner script or directly form the 
testcase folder with the runner script: *run.sh*.

For detailed description, check the help menu with *-h*.

## Installation

The testframework has some additional dependencies. To install these dependencies
run the *install_requirements.sh* script.

## Configuration

The easiest way to create a new testcase is to copy one of the existing testcases
which implements the closest testcase compared to the desired test.

The *example* sub-folder contains a skeleton testcase which also can be used as a 
starting point for any new testcase. The example configuration file brings an
example for all the available parameters that can be set in the configurations.

The testcase classes which implements the components and features for the different
test scenarios can be found in the *testframework/testcases* sub-folder.
The *TestCase* classes directly gets the configuration as constructor parameters
so every testcase uses only the relevant part of the available config set.
Several configuration parameters are meant for the testframework thereby these
are ignored by the testcase classes.
 

## Run

To run the testcases, use the *run_test.py* script.
The script reads the *test* folder and read all the testcase sub-folders whose
name start with the prefix *case*.

The result of the test is printed on the console and also dumped into a file,
called *results.xml* for any CI environment.

The *dockerized-test.sh* script is created for running the test in Docker
environment. The script builds a test Docker image with all the necessary 
configurations and initiates the main runner script.

## Maintainers

  * Janos Czentye
  * Balazs Nemeth
  * Lajos Gerecs

