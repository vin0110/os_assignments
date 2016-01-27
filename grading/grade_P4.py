#!/usr/bin/python

import sys
import os
from time import sleep
import subprocess
import threading
import signal

from command import *
from utils import *

from P4_grader import *

def main(argv):

	section = argv[0]
	hw_dir = argv[1]
	hw_output_dir = argv[2]
	student_id = raw_input("Please enter student uid: ")

	Command("mkdir -p %s" % hw_dir).execute()
	Command("mkdir -p %s" % hw_output_dir).execute()


	student_dir = os.path.join(hw_dir, student_id)	
	student_output_dir = os.path.join(hw_output_dir, student_id)

	print "Grading %s" % student_id
	program_path = compile(student_dir, student_output_dir)
	if program_path is not None and os.path.exists(program_path):
		print "\tCompilation: pass"
	else:
		print("\tcompilation: fail")
	results = grade_hw("P4", student_id, student_dir, student_output_dir)
	#output_file = os.path.join(student_result_dir, "score.txt")
        #:report_grading(results, output_file)
	

if __name__ == "__main__":
	main(sys.argv[1:]) 
