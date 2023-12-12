# Simple Proxy Server

## Introduction
Building a simple transparent proxy server, without using any 3rd party libraries
The two key features of this proxy server:
1. Domain-Level Redirection
   Redirect any url containing “korea” to "http://mnet.yonsei.ac.kr/"
3. Image Filtering
   With "?img_off" option in request, drop all the image files

## Usage
'''
$ python prx.py <port>
'''
