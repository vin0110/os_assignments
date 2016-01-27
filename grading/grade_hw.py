#!/usr/bin/python

import sys
import os
from time import sleep
import subprocess
import threading
import signal

from command import *
from utils import *

from auto_grading import *

def main(argv):

	hw_id = argv[0]
	section = argv[1]
	hw_dir = argv[2]
	hw_execution_dir = argv[3]
	hw_result_dir = argv[4]
	student_id = raw_input("Please enter student uid: ")

	Command("mkdir -p %s" % hw_dir).execute()
	Command("mkdir -p %s" % hw_execution_dir)
	Command("mkdir -p %s" % hw_result_dir).execute()


	student_dir = os.path.join(hw_dir, student_id)	
	student_execution_dir = os.path.join(hw_execution_dir, student_id)
	student_result_dir = os.path.join(hw_result_dir, student_id)

	print "Grading %s" % student_id
	(output_lib, flag) = compile(student_dir, student_result_dir)
	if os.path.exists(output_lib):
		print "\tCompilation: pass"
	else:
		print("\tcompilation: fail")
	results = grade_hw(hw_id, output_lib, student_execution_dir, student_result_dir, flag)
	output_file = os.path.join(student_result_dir, "score.txt")
        report_grading(results, output_file)
	

if __name__ == "__main__":
	main(sys.argv[1:]) 
