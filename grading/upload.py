#!/usr/bin/python

import sys
import os
from time import sleep
import subprocess
import threading
import signal

from command import *
from utils import *

def upload_graded_hw(sec, hw_id, hw_output_dir, user, return_name):
	tmp_dir = "/tmp/upload_%s_%s" % (sec, hw_id)
	Command("mkdir -p %s" % tmp_dir)

	for student in os.listdir(hw_output_dir):
		print 'Processing %s' % student
		student_tmp_dir = "%s/%s" % (tmp_dir, student)
		student_tmp_file = "%s/%s" % (student_tmp_dir, return_name)
		Command("mkdir -p %s" % student_tmp_dir).execute()
		Command("cd %s && tar zcf %s %s" % (hw_output_dir, student_tmp_file, student)).execute()

	hw_return_dir = "/afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/graded/%s" % (sec, hw_id)
	os.system("ssh chsu6@remote-linux.eos.ncsu.edu mkdir -p %s" % hw_return_dir)
	os.system("scp -r %s/* %s@remote-linux.eos.ncsu.edu:%s" % (tmp_dir, user, hw_return_dir))
	#print "scp -rf %s/* %s@remote-linux.eos.ncsu.edu:%s" % (tmp_dir, user, hw_return_dir)
		

def main(argv):

	hw_id = argv[0]
	section = argv[1]
	hw_output_dir = argv[2]
	return_name = argv[3] if len(argv) == 4 else "%s.tar.gz" % hw_id
	hw_return_dir = "/afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/graded/%s" % (section, hw_id)
	user = raw_input("Please enter your unity id: ")
	
	upload_graded_hw(section, hw_id, hw_output_dir, user, return_name)

if __name__ == "__main__":
	main(sys.argv[1:]) 
