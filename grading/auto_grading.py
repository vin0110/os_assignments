#!/usr/bin/python

import sys
import os
from time import sleep
import subprocess
import threading
import signal

from command import *
from utils import *

supported_compress_format_list = ['tar.gz', 'tar.bz2', 'tgz', 'tar', 'zip']

def is_supported_file_format(f):
	for format in supported_compress_format_list:
		if f.endswith(format):
			return True
	return False

def decompress_file(f, dest_dir):
	if not os.path.isfile(f):
		return
	if not is_supported_file_format(f):
		return
	
	extracted_dir = os.path.join(os.path.dirname(f), 'hw_extracted')
	Command("mkdir -p %s" % extracted_dir).execute()

	cmd = None
	# avoid wrong file exetension
	if f.endswith("tar.gz") or f.endswith("tgz") or f.endswith("tar"):
		cmd = Command("tar zxvf '%s' -C %s" % (f, extracted_dir))
		cmd = Command("tar xvf '%s' -C %s" % (f, extracted_dir))
	elif f.endswith("zip"):
		cmd = Command("unzip -o '%s' -d %s" % (f, extracted_dir))

	if cmd is not None:
		#print cmd.command
		cmd.execute()
		#print cmd.output
	else:
		print "not compression file found"
	
	target_dir = locate_makefile_dir(extracted_dir)
	if target_dir is not None:
		Command("mv '%s'/* %s" % (target_dir, dest_dir)).execute()
	else:
		Command("mv '%s'/* %s" % (extracted_dir, dest_dir)).execute()
		
def preprocess_dir(student_dir):
	#print 'Processing student: %s' % student_dir
	upload_files = [{'file': os.path.join(student_dir, f), 'date': os.path.getmtime(os.path.join(student_dir, f))} for f in os.listdir(student_dir) if (os.path.isfile(os.path.join(student_dir, f)) and is_supported_file_format(f))]
	#print upload_files
	upload_files.sort(key=lambda item:item['date'], reverse=True)
	latest_file = upload_files[0]['file'] if len(upload_files) > 0 else ''
	#print 'The latest file in %s is %s' % (student_dir, latest_file)
	if latest_file is not '':
		decompress_file(latest_file, student_dir)
		
	Command("cd %s; rm -f *.out *.o *.a" % student_dir).execute()

def compile(student_dir, student_result_dir):
	cmd = Command("cd %s; rm -f *.o *.a; make > %s/make.out" % (student_dir, student_result_dir))
	#print cmd.command
	cmd.execute()
	#print cmd.output

	cmd_flag = Command("grep m32 %s/*akefile" % student_dir)
	cmd_flag.execute()
	flag_output = cmd_flag.output.strip()
	flag = "m32" if len(flag_output) > 0 else None
		
	output_lib = os.path.join(student_dir, "mythread.a")
	# avoid wrong output
	Command("mv %s/libmythread.a %s " % (student_dir, output_lib)).execute()
	if os.path.exists(output_lib):
		return (output_lib, flag)
	return (None, flag)
		
	

def prepare_hw_environment(hw_id, output_lib, student_execution_dir, student_result_dir, flag=None):
	Command("cp -r %s/* %s" % (hw_id, student_execution_dir)).execute()
	if flag is not None:
		Command("cp %s/Makefile32 %s/Makefile" % (hw_id, student_execution_dir)).execute()
	Command("cp %s %s" % (output_lib, student_execution_dir)).execute()
	Command("cd %s; make clean; make > %s/link.out 2>&1" % (student_execution_dir, student_result_dir)).execute()
	
def grade_hw(hw_id, output_lib, student_execution_dir, student_output_dir, flag=None):
	if output_lib is None or not os.path.exists(output_lib):
		return None
	
	prepare_hw_environment(hw_id, output_lib, student_execution_dir, student_output_dir, flag)
	testcases = {
		1: "%s/testcase_passing 1",
		2: "%s/testcase_passing 100",
		3: "%s/testcase_passing 1 1",
		4: "%s/testcase_passing 20 1",
		5: "%s/testcase_passing 1 2",
		6: "%s/testcase_passing 1 3",
		7: "%s/testcase_semaphore 0 0",
		8: "%s/testcase_semaphore 1 1",
		9: "%s/testcase_semaphore 3 1",
		10: "%s/testcase_semaphore 1 3",
		11: "%s/testcase_passing 20 2",
		12: "%s/testcase_passing 40 2",
		13: "%s/testcase_joinall 100",
		14: "%s/testcase_joinall 10 1",
		15: "%s/testcase_joinall 10 2",
		16: "%s/testcase_joinall 3 3",
		17: "%s/testcase_joinall 0 1",
		18: "%s/testcase_semaphore 1 1 1",
	}
	result_list = {}
	for (testcase_id, testcase_cmd) in testcases.items():
		testcase_answer = os.path.join(student_execution_dir, "output", "testcase_%s.txt" % testcase_id)
                student_answer = os.path.join(student_output_dir, "testcase_%s.txt" % testcase_id)

		cmd_test = Command("%s > %s 2>&1" % (testcase_cmd % student_execution_dir, student_answer))
		cmd_test.execute()
		cmd_verify = Command("diff %s %s" % (testcase_answer, student_answer))
                cmd_verify.execute()

		result_pass = True if cmd_test.completed and len(cmd_verify.output.strip()) == 0 else False
                result_completed = cmd_test.completed
                result_list[testcase_id] = {"pass": result_pass, "completed": result_completed}

		if cmd_test.completed:
                        print "\ttestcase_%s: %s" % (testcase_id, "pass" if result_pass else "fail")
                else:
                        print "\ttestcase_%s: timeout" % testcase_id

	print "\tscore: %s" % calculate_score(result_list)	
	# workaround to kill zombie processes
        Command("ps aux | grep testcase_ | tr -s ' ' | cut -d' ' -f2 | xargs kill -9").execute()
	return result_list

def calculate_score(results):
	if results is None:
		return 0
	score_basic_table = {
		0: 0,
		1: 6,
		2: 11,
		3: 16,
		4: 20,
		5: 24,
		6: 27,
		7: 30,
		8: 33,
		9: 35,
		10: 37,
	}
	score = 0
	score_compilation = 50
	num_basic = 0
	num_advanced = 0
	num_exceptional = 0
	for (testcase_id, result) in results.items():
		count = 1 if result['pass'] else 0 
		if testcase_id <= 10:
			num_basic += count
		elif testcase_id >= 16:
			num_exceptional += count
		else:
			num_advanced+= count
	score = score_compilation + score_basic_table[num_basic] + 2 * num_advanced + 1 * num_exceptional
	return score

def get_student_info(student_dir):
	student_info = dict()
	student_info['id'] = student_dir
	return student_info

def report_grading(results, output_file):
	if results is None:
		with open(output_file, "w") as f:
			f.write("Your program is not evaluated because of compilation problems\n")
	else:
		with open(output_file, "w") as f:
			for testcase in sorted(results.keys()):
				result = results[testcase]
				comment = "pass" if result["pass"] else "fail" if result['completed'] else "timeout"
				f.write("%s: %s\n" % (testcase, comment))
			grade = calculate_score(results)
			f.write("\nTotal: %s\n" % grade)
		

def create_score_sheet(hw_results, output_file):
	with open(output_file, "w") as f:
		headers = [str(s) for s in sorted(hw_results[hw_results.keys()[0]].keys())]
		f.write("uid,")
		f.write(",".join(headers))
		f.write(",total\n")

		for (uid, results) in hw_results.items():
			f.write(uid)
			if results is None:
				f.write(",")
				f.write(",".join(["null"] * len(headers)))
			else:
				for testcase in sorted(results.keys()):
                        		f.write(",%s" % ("pass" if results[testcase]["pass"] else "fail"))

			grade = calculate_score(results)
			f.write(",%s\n" % grade)

def batch_processing(hw_id, hw_dir, hw_execution_dir, hw_output_dir, hw_sheet, notification):
	hw_results = {}
	for student in os.listdir(hw_dir):
		print 'Grading %s' % student
		# prepare environment
		student_info = get_student_info(student)
                student_id = student_info['id']
		student_dir = os.path.join(hw_dir, student)
		student_execution_dir = os.path.join(hw_execution_dir, student)
		student_output_dir = os.path.join(hw_output_dir, student)
		Command('mkdir -p %s' % student_execution_dir).execute()
		Command('mkdir -p %s' % student_output_dir).execute()
		
		# steps
		preprocess_dir(student_dir)
		(output_lib, flag) = compile(student_dir, student_output_dir)

		# cannot create mythread.a
		if output_lib is None:
			print '\tCompilation: fail'
			#print "%s: fail" % student
			if notification:
                                notify_student(student, hw_id)
				# avoid to be sapm mails	
				sleep(5)
		else:
			print '\tCompilation: pass'

		results = grade_hw(hw_id, output_lib, student_execution_dir, student_output_dir, flag=flag)
		output_file = os.path.join(student_output_dir, "score.txt")
		report_grading(results, output_file)
		hw_results[student] = results

	create_score_sheet(hw_results, hw_sheet)

def notify_student(student_id, hw_id):
	print "* Send notification mail for compilation problem: %s" % student_id
	name_from = "Chin-Jung Hsu"
	email_from = "chsu6@ncsu.edu"
	name_to = student_id
	email_to = "%s@ncsu.edu" % student_id
	subject = "CSC501 - Your %s submission has compilation problems" % hw_id
	message = "Hi %s,\n\n\tThis is just a reminder that our auto-grader program cannot compile your %s submission successfully.  This is either a compilation problem or mythread.a is missing.  Please solve your compilation problem first.  Then, wee will let you know what you should do." % (name_to, hw_id)
	#print message	
	send_email(name_from, email_from, name_to, email_to, subject, message)

def download_hw(hw, section, dest, user):
	#cmd = Command("cp -r /afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/submitted/%s/* % s" % (section, hw, dest))
	cmd = Command("scp -r %s@remote-linux.eos.ncsu.edu:/afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/submitted/%s/* % s" % (user, section, hw, dest))
	#print cmd.command
	cmd.execute()
	#print cmd.output

def main(argv):

	hw_id = argv[0]
	section = argv[1]
	hw_dir = argv[2]
	hw_execution_dir = argv[3]
	hw_result_dir = argv[4]
	hw_sheet = argv[5]
	notification = argv[6].lower() in ["true", "yes", "1"]
	user = raw_input("Please enter your unity id: ")

	Command("mkdir -p %s" % hw_dir).execute()
	Command("mkdir -p %s" % hw_execution_dir)
	Command("mkdir -p %s" % hw_result_dir).execute()
	download_hw(hw_id, section, hw_dir, user)
	batch_processing(hw_id, hw_dir, hw_execution_dir, hw_result_dir, hw_sheet, notification)

if __name__ == "__main__":
	main(sys.argv[1:]) 
