#!/bin/python3

import json
import os

def system(cmd):
    res = os.system(cmd % os.environ)
    if res != 0:
        raise Exception("Error on cmd %s" % cmd)

def main():
    with open("versions.json") as f:
        versions = json.load(f)

    print("Checking out %s/exccd/%s" % (versions["exccdOwner"], versions["exccdCommit"]))
    system("git clone https://github.com/%s/exccd %%(GOPATH)s/src/github.com/EXCCoin/exccd" % versions["exccdOwner"])
    system("cd %(GOPATH)s/src/github.com/EXCCoin/exccd && git checkout " + versions["exccdCommit"])

    print("Checking out %s/exccwallet/%s ", (versions["exccwalletOwner"], versions["exccwalletCommit"]))
    system("git clone https://github.com/%s/exccwallet %%(GOPATH)s/src/github.com/EXCCoin/exccwallet" % versions["exccwalletOwner"])
    system("cd %(GOPATH)s/src/github.com/EXCCoin/exccwallet && git checkout " + versions["exccwalletCommit"])

    print("Checking out %s/exilibrium/%s ", (versions["exilibriumOwner"], versions["exilibriumCommit"]))
    system("git clone https://github.com/%s/exilibrium %%(GOPATH)s/src/github.com/EXCCoin/exilibrium" % versions["exilibriumOwner"])
    system("cd %(GOPATH)s/src/github.com/EXCCoin/exilibrium && git checkout " + versions["exilibriumCommit"])

if __name__ == "__main__":
    main()