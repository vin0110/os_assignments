#!/usr/bin/python

import sys
import os
from time import sleep
import subprocess
import threading
import signal

from command import *
from utils import *

supported_compress_format_list = ['tar.gz', 'tar.bz2', 'tgz', 'tar', 'zip', 'rar']

def signal_handler(signal, frame):
	return

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
	elif f.endswith("rar"):
		cmd = Command("unrar e '%s' %s" % (f, extracted_dir))

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
	Command("if [ -x ramdisk ]; then rm ramdisk; fi").execute()

def compile(student_dir, student_output_dir):
	cmd = Command("cd %s; rm -f *.o *.a; make > %s/make.out" % (student_dir, student_output_dir))
	#print cmd.command
	cmd.execute()
	#print cmd.output

	output_lib = os.path.join(student_dir, "ramdisk")
	if os.path.exists(output_lib):
		return output_lib
	return None
		
def prepare_environment(student_dir, student_output_dir, testcase_dir):
	Command("cp -r %s/* %s" % (testcase_dir, student_output_dir)).execute()	
	Command("rm -rf %s/results; mkdir -p %s/results" % (student_output_dir, student_output_dir)).execute()
	Command("rm -rf %s/mount; mkdir -p %s/mount" % (student_output_dir, student_output_dir)).execute()
	Command("cp %s/ramdisk %s" % (student_dir, student_output_dir)).execute()

def grade_hw(hw_id, student_id, student_dir, student_output_dir):
	if not os.path.exists(os.path.join(student_dir, "ramdisk")):
		return None

	signal.signal(signal.SIGTERM, signal_handler)

	timeout = 5
	testcase_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), hw_id)

	# copy necessary files
	prepare_environment(student_dir, student_output_dir, testcase_path)

	cwd = os.getcwd()
        os.chdir(student_output_dir)

	total_cases = 19

	result_list = {}
	for testcase_id in range(1, total_cases+1):
		#print "grading %s" % testcase_id
		student_testcase_returncode = os.path.join("results", "test%s.returncode" % testcase_id)

		cmd_test = None
		cmd_test_command = None
		isException = False

		cmd_test_command="bash testcases/test%s" % testcase_id
		cmd_test = Command("/usr/bin/timeout --signal=SIGKILL %s %s; echo $? > %s" % (timeout, cmd_test_command, student_testcase_returncode))

		isException = False
		try:
			#print cmd_test.command
			#Command("echo \"%s\" > %s/testcmd_%s" % (cmd_test_command, student_output_dir, testcase_id)).execute()
			#subprocess.Popen("testcases/kill.sh %s student_testcase_returncode ramdisk" % timeout, shell=True)
			subprocess.Popen("sleep %s; if [ ! -f %s ]; then killall -9 ramdisk; fi" % (timeout, student_testcase_returncode), shell=True)
			os.system(cmd_test.command)
			#cmd_test.execute()
		except Exception as e:
			isException = True
			print e

		cmd_returncode = Command("cat %s" % student_testcase_returncode)
                cmd_returncode.execute()
                returncode = int(cmd_returncode.output.strip())
		#print "returcode=%s" % returncode

                result_list[testcase_id] = {"pass": returncode == 0}
		result = result_list[testcase_id]
		test_result = "pass" if result["pass"] else "fail"

		print "\ttestcase_%s: %s" % (testcase_id, test_result)


	print "\tscore: %s" % calculate_score(result_list)	

	for testcase_id in range(1, total_cases+1):
		os.system("fusermount -u mount/test%s > /dev/null 2>&1" % testcase_id)

	os.chdir(cwd)
	return result_list

def calculate_score(results):
	if results is None:
		return 0
	score = 0
	score_compilation = 50
	num_basic = 0
	num_regular_postmark = 0
	num_exceptional_postmark = 0
	for (testcase_id, result) in results.items():
		count = 1 if result['pass'] else 0 
		if testcase_id <= 15:
			num_basic += count
		elif testcase_id <= 18:
			num_regular_postmark += count
		elif testcase_id == 19:
			num_exceptional_postmark += count
	score = score_compilation + num_basic * 1 + num_regular_postmark * 10 + num_exceptional_postmark * 5
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
				comment = "pass" if result["pass"] else "fail"
				f.write("%s: %s\n" % (testcase, comment))
			grade = calculate_score(results)
			f.write("\nTotal: %s\n" % grade)
		

def create_score_sheet(hw_results, output_file):
	headers = []
	for student in hw_results:
		if hw_results[student] is not None:
			headers = [str(s) for s in sorted(hw_results[student].keys())]
			break
	
	with open(output_file, "w") as f:
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
					result = results[testcase]
					comment = "pass" if result["pass"] else "fail"
                        		f.write(",%s" % comment)

			grade = calculate_score(results)
			f.write(",%s\n" % grade)

def batch_processing(hw_id, hw_dir, hw_output_dir, hw_sheet, notification):
	hw_results = {}
	for student in os.listdir(hw_dir):
		print 'Grading %s' % student

		# prepare environment
		student_info = get_student_info(student)
                student_id = student_info['id']
		student_dir = os.path.join(hw_dir, student)
		student_output_dir = os.path.join(hw_output_dir, student)
		Command('mkdir -p %s' % student_output_dir).execute()
		
		# steps
		preprocess_dir(student_dir)
		program_path = compile(student_dir, student_output_dir)

		# cannot create mythread.a
		
		if program_path is None:
			print '\tCompilation: fail'
			#print "%s: fail" % student
			if notification:
                                notify_student(student, hw_id)
				# avoid to be sapm mails	
				sleep(5)
		else:
			print '\tCompilation: pass'

		results = grade_hw(hw_id, student_id, student_dir, student_output_dir)
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
	message = "Hi %s,\n\n\tThis is just a reminder that our auto-grader program cannot compile your %s submission successfully.  It can be a compilation problem or the executable file 'ramdisk' cannot be found.  Please solve your compilation problem soon.  We only accept quick fix by 3 P.M. today.  Please send us your updated files by mail." % (name_to, hw_id)
	#print message	
	send_email(name_from, email_from, name_to, email_to, subject, message)

def download_hw(hw, section, dest, user):
	#cmd = Command("cp -r /afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/submitted/%s/* % s" % (section, hw, dest))
	cmd = Command("scp -r %s@remote-linux.eos.ncsu.edu:/afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/submitted/%s/* % s" % (user, section, hw, dest))
	#print cmd.command
	cmd.execute()
	#print cmd.output

def main(argv):

	hw_id = "P4"
	section = argv[0]
	hw_dir = argv[1]
	hw_output_dir = argv[2]
	hw_sheet = argv[3]
	notification = argv[4].lower() in ["true", "yes", "1"]
	user = raw_input("Please enter your unity id: ")

	Command("mkdir -p %s" % hw_dir).execute()
	Command("mkdir -p %s" % hw_output_dir).execute()
	download_hw(hw_id, section, hw_dir, user)
	batch_processing(hw_id, hw_dir, hw_output_dir, hw_sheet, notification)

if __name__ == "__main__":
	main(sys.argv[1:]) 
