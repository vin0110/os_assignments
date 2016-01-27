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

def compile(student_dir, student_output_dir):
	cmd = Command("cd %s; rm -f *.o *.a; make > %s/make.out" % (student_dir, student_output_dir))
	#print cmd.command
	cmd.execute()
	#print cmd.output

	output_lib = os.path.join(student_dir, "ush")
	if os.path.exists(output_lib):
		return output_lib
	return None
		
def prepare_environment(student_dir, student_output_dir, testcase_dir):
	Command("cp -r %s/* %s" % (testcase_dir, student_output_dir)).execute()	
	Command("cp %s/ush %s" % (student_dir, student_output_dir)).execute()
	Command("rm -f ~/.ushrc").execute()
	Command("rm -rf %s/results; rm -rf %s/output; mkdir -p %s/results; mkdir -p %s/output" % (student_output_dir, student_output_dir, student_output_dir, student_output_dir)).execute()

def grade_hw(hw_id, student_id, student_dir, student_output_dir):
	if not os.path.exists(os.path.join(student_dir, "ush")):
		return None

	signal.signal(signal.SIGTERM, signal_handler)

	total_cases = 35
	timeout = 3
	# True: has output at /tmp/test.file, False: no output
	output_types = {
		1: False, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False,
		8: False, 9: True, 10: True, 11: True, 12: True, 13: True,
		14: False, 15: False, 16: False, 17: False, 18: False, 19: True,
		20: False, 21: False, 22: False, 23: False, 24: False, 25: False, 26: False, 27: False,
		28: True, 29: True,
		30: False, 31: True, 32: True, 33: True, 34: False, 35: False,
        }
	verifycmds = {
		22: "grep \"buil\\|bin\" %s",
		24: "grep -v course %s",
	}

	testcase_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), hw_id)
	
	# copy necessary files
	prepare_environment(student_dir, student_output_dir, testcase_path)

	cwd = os.getcwd()
        os.chdir(student_output_dir)

	result_list = {}
	for testcase_id in range(1, total_cases+1):

		#Command("cp %s/.ushrc ~" % testcase_path).execute()
		if testcase_id == 30:
			Command("cp %s/.ushrc ~" % testcase_path).execute()
		else:
			Command("rm -f ~/.ushrc").execute()

		student_testcase_answer = os.path.join("answer", "test.%s.expected" % testcase_id)
		student_testcase_path = os.path.join("testcases", "test.%s" % testcase_id)
		student_testcase_output = os.path.join("output", "test.%s.output" % testcase_id)
		student_testcase_result = os.path.join("results", "test.%s.out.txt" % testcase_id)
		student_testcase_grep = os.path.join("results", "test.%s.grep" % testcase_id)
		student_testcase_returncode = os.path.join("results", "test.%s.returncode" % testcase_id)

		cmd_test = None
		cmd_test_command = None
		isException = False

		if output_types[testcase_id]:
			cmd_test_command = "./ush < %s >& /dev/null" % student_testcase_path
		else:
			cmd_test_command = "./ush < %s >& %s" % (student_testcase_path, student_testcase_result)

		cmd_test = Command("/usr/bin/timeout --signal=SIGKILL %s %s; echo $? > %s" % (timeout, cmd_test_command, student_testcase_returncode))

		isException = False
		try:
			#print cmd_test.command
			Command("echo \"%s\" > %s/testcmd_%s" % (cmd_test_command, student_output_dir, testcase_id)).execute()
			cmd_test.execute(async=True)
			if testcase_id == 28 or testcase_id == 29:
				os.system("pgrep -f './ush' | xargs kill -%s" % ("3" if testcase_id == 28 else "15"))
			cmd_test.wait()
		except Exception as e:
			isException = True

		if testcase_id == 27:
                        sleep(2)

		cmd_returncode = Command("cat %s" % student_testcase_returncode)
                cmd_returncode.execute()
                returncode = int(cmd_returncode.output.strip())
                isCompleted = returncode == 0

		os.system("pgrep -f './ush' | xargs kill -9")

		#print cmd_test.returncode, cmd_test.command

		if os.path.exists(os.path.join(student_output_dir, student_testcase_result)) and os.path.getsize(os.path.join(student_output_dir, student_testcase_result)) > 4096:
                        Command("cd %s; rm -f %s; echo the output is too large!!! > %s" % (student_output_dir, student_testcase_result, student_testcase_result)).execute()
                if os.path.exists(os.path.join(student_output_dir, student_testcase_output)) and os.path.getsize(os.path.join(student_output_dir, student_testcase_output)) > 4096:
                        Command("cd %s; rm -f %s; echo the output is too large!!! > %s" % (student_output_dir, student_testcase_output, student_testcase_output)).execute()
                if os.path.exists(os.path.join(student_output_dir, student_testcase_grep)) and os.path.getsize(os.path.join(student_output_dir, student_testcase_grep)) > 4096:
                        Command("cd %s; rm -f %s; echo the output is too large!!! > %s" % (student_output_dir, student_testcase_grep, student_testcase_grep)).execute()
		

		student_target_output = student_testcase_output if output_types[testcase_id] else student_testcase_result
		cmd_veriry = None
		isVerified = False 
		if os.path.exists(student_target_output) and os.path.getsize(student_target_output) > 0:
			isVerified = True
			if testcase_id not in verifycmds:
				cmd_verify = Command("grep -i \"`cat %s`\" %s >& %s" % (student_testcase_answer, student_target_output, student_testcase_grep))
			else:
				cmd_verify = Command("%s > %s" % (verifycmds[testcase_id] % student_target_output, student_testcase_grep))
	
			#print cmd_verify.command
			cmd_verify.execute()
			#print cmd_verify.returncode, cmd_verify.command

		result_pass = cmd_verify.returncode == 0 if returncode  != 137 and isVerified else False
                result_list[testcase_id] = {"pass": result_pass, "timeout": returncode == 137, "exception": isException or returncode == 134 or returncode == 139}
		result = result_list[testcase_id]
		test_result = "pass" if result["pass"] else "timeout" if result['timeout'] else "exception" if result['exception'] else "fail"

		#print returncode, cmd_verify.returncode
		print "\ttestcase_%s: %s" % (testcase_id, test_result)


	print "\tscore: %s" % calculate_score(result_list)	

	os.chdir(cwd)
	return result_list

def calculate_score(results):
	if results is None:
		return 0
	score = 0
	score_compilation = 50
	num_basic = 0
	num_advanced = 0
	num_exceptional = 0
	for (testcase_id, result) in results.items():
		count = 1 if result['pass'] else 0 
		if testcase_id <= 15 or 20 <= testcase_id <= 24:
			num_basic += count
		elif 16 <= testcase_id <= 19 or 25 <= testcase_id <= 30:
			num_advanced += count
		else:
			num_exceptional+= count
	score = score_compilation + num_basic * 1.5 + num_advanced * 1.5 + num_exceptional * 1
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
				comment = "pass" if result["pass"] else "timeout" if result['timeout'] else "exception" if result['exception'] else "fail"
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
					result = results[testcase]
					comment = "pass" if result["pass"] else "timeout" if result['timeout'] else "exception" if result['exception'] else "fail"
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
	message = "Hi %s,\n\n\tThis is just a reminder that our auto-grader program cannot compile your %s submission successfully.  It can be a compilation problem or the executable file 'ush' cannot be found.  Please solve your compilation problem soon.  We only accept quick fix by today.  Please send us your updated file by mail." % (name_to, hw_id)
	#print message	
	send_email(name_from, email_from, name_to, email_to, subject, message)

def download_hw(hw, section, dest, user):
	#cmd = Command("cp -r /afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/submitted/%s/* % s" % (section, hw, dest))
	cmd = Command("scp -r %s@remote-linux.eos.ncsu.edu:/afs/eos.ncsu.edu/courses/csc/csc501/lec/%s/submitted/%s/* % s" % (user, section, hw, dest))
	#print cmd.command
	cmd.execute()
	#print cmd.output

def main(argv):

	hw_id = "P2"
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
