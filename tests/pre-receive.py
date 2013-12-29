#!/usr/bin/python
# -*- coding: utf8 -*-
import os, errno
import sys   # system stuff
import subprocess
import atexit


remotedir = "REMOTE"
localdir  = "LOCAL"
rootdir = ""

def runCommand(cmd,expected_returncode):
	retval = 0
	output = None
	try:
		output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
	except subprocess.CalledProcessError as e:
		retval = e.returncode
		output = e.output

	print( "CMD: " + cmd )
	if retval != expected_returncode:
		print( output )
		print( "RETVAL: %d != %d" % (retval, expected_returncode) )
		sys.exit(1)

def rm_rf(d):
    for path in (os.path.join(d,f) for f in os.listdir(d)):
        if os.path.isdir(path):
            rm_rf(path)
        else:
            os.unlink(path)
    os.rmdir(d)


def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc: # Python >2.5
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else: raise


def initializeRepos():
	global rootdir
	rootdir = os.getcwd()

	# Remote
	mkdir_p(remotedir)
	os.chdir(remotedir)
	runCommand("git init --bare --shared", 0)
	runCommand("git config receive.denyNonFastForwards false", 0)
	runCommand("cp  ../../hooks/pre-receive hooks/", 0)
	runCommand("chmod +x hooks/pre-receive", 0)
	os.chdir(rootdir)

	# Local
	runCommand("git clone ./%s %s" % (remotedir, localdir), 0)
	os.chdir(localdir)
	runCommand("git config user.email user@doamin.com",0)
	runCommand("git config user.name 'John Doe'",0)
	os.chdir(rootdir)



def cleanupRepos():
	os.chdir(rootdir)
	rm_rf(remotedir)
	rm_rf(localdir)


atexit.register(cleanupRepos)
initializeRepos()

os.chdir(localdir)

# Create initial commit without Signed-off-by
runCommand("git commit -m '[SM-] Initial commit' --allow-empty", 0)

# check that it can not be pushed
runCommand("git push origin -u master", 1)

# Check that adding the Signed-off-by still not allows the commit to be pushed
runCommand("git commit --amend -s --no-edit --allow-empty", 0)
runCommand("git push origin -u master", 1)

# Check that adding an issue number allow it to be pushed
runCommand("git commit --amend -s --allow-empty -m '[SM-9] Initial commit'", 0)
runCommand("git push origin -u master", 0)

# Test that master can not be removed
runCommand("git push origin :master", 1)

# Create branches for tests
runCommand("git checkout -b test-public", 0)
runCommand("git checkout -b test-private", 0)

### Test that we can do what ever we want in private branches
# Test branch creation
runCommand("git push origin HEAD:user/new_branch", 0)

# Test branch fast-forward of commit without Signed-off-by and JIRA-issue
runCommand("git commit -m 'Some change' --allow-empty", 0)
runCommand("git push origin HEAD:user/new_branch", 0)

# Test branch rewind
runCommand("git push    origin HEAD~1:user/new_branch", 1)
runCommand("git push -f origin HEAD~1:user/new_branch", 0)

# Test branch deletion
runCommand("git push origin :user/new_branch", 0)


runCommand("git checkout test-public", 0)
## Test that we are limited in toplevel branches

# Test that commits without Signed-off-by can not be pushed
runCommand("git push origin HEAD:new_branch", 0)
runCommand("git commit -m 'commit without signed-off' --allow-empty", 0)
runCommand("git push    origin HEAD:new_branch", 1)
runCommand("git push -f origin HEAD:new_branch", 1)

# Test that Signed-off-by commit can be pushed
runCommand("git commit --amend -s --allow-empty -m 'commit with signed-off [SM-12345]'", 0)
runCommand("git push    origin HEAD:new_branch", 0)

# Test that a normal branch merge with missing JIRA-issue can not be pushed
runCommand("git checkout -b feature", 0)
runCommand("git commit -m '[SM-0] commit1 without signed-off' --allow-empty", 0)
runCommand("git commit -m 'commit2 [SM-01] without signed-off' --allow-empty", 0)
runCommand("git commit -m 'commit3 without [SM-012] signed-off' --allow-empty", 0)
runCommand("git commit -m 'commit4 without signed-off' --allow-empty", 0)
runCommand("git checkout test-public", 0)
runCommand("git merge --no-edit --no-ff feature", 0)
runCommand("git push    origin HEAD:new_branch", 1)

# Test that fixing the missing JIRA-issue make the branch merge and push
runCommand("git reset --hard HEAD~1", 0)
runCommand("git checkout feature", 0)
runCommand("git commit -m 'commit4 without signed-off [SM-0123]' --allow-empty --amend", 0)
runCommand("git checkout test-public", 0)
runCommand("git merge --no-edit --no-ff feature", 0)
runCommand("git push    origin HEAD:new_branch", 1)

# Test that a Signed-off merge can be pushed
runCommand("git commit --amend -s --no-edit", 0)
runCommand("git push    origin HEAD:new_branch", 0)

# Test that branch rewind is not possible
runCommand("git reset --hard HEAD~1", 0)
runCommand("git push origin HEAD:new_branch", 1)
runCommand("git push -f origin HEAD:new_branch", 1)

# Test that delete-crete rewind is possible
runCommand("git push    origin :new_branch", 0)
runCommand("git push -f origin HEAD:new_branch", 0)

print( "Tests passed." )
sys.exit(0)