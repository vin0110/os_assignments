import subprocess
import threading
import signal

class TimeoutException(Exception):
	pass
class Command(object):
    def __init__(self, command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        self.command = command
        self.shell = shell
	self.stdin = stdin
	self.stdout = stdout
	self.stderr = stderr

    def execute(self, async=False):
	self.process = subprocess.Popen(self.command, shell=self.shell, stdout=self.stdout, stderr=self.stderr)
        self.pid = self.process.pid
        self.output, self.error = self.process.communicate()
	if not async:
		self.process.wait()
        return self.returncode

    def wait(self):
	self.process.wait()

    @property
    def returncode(self):
        return self.process.returncode

class TaskCommand(threading.Thread):
    def __init__(self, command, timeout=None, shell=True):
        threading.Thread.__init__(self)
        self.isTimeout = False
	self.hasException = False
        self.command = command
        self.timeout = timeout
        self.shell = shell
	self.setDaemon(True)

    def run(self):
        self.process = subprocess.Popen(self.command, shell=self.shell, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        self.pid = self.process.pid
        self.output, self.error = self.process.communicate()
        self.process.wait()

    def execute(self):
        self.start()
        self.join(self.timeout)
	if self.is_alive():
        	self.isTimeout = True
                try:
                	#self.process.terminate()
                        #self.join(1)
			pass
                except:
                       	pass
        return self.returncode

    @property
    def returncode(self):
        return self.process.returncode

class Command1():
    def __init__(self, command, timeout=5, shell=True):
        self.completed = False
	self.exception = False
        self.command = command
        self.timeout = timeout
        self.shell = shell
	self.output = None
	signal.signal(signal.SIGALRM, self.timeout_handler)
	signal.signal(signal.SIGTERM, self.terminate_handler)

    def timeout_handler(self, signum, frame):
	self.completed = False
	self.exception = True
        raise TimeoutException

    def terminate_handler(self, signum, frame):
	self.output = None
	self.completed = False
	self.exception = True
	#raise Exception("terminate")

    def execute(self):
	try:
		self.process = subprocess.Popen(self.command, shell=self.shell, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        	self.pid = self.process.pid
        	self.output, self.error = self.process.communicate()
		signal.alarm(self.timeout)
		self.process.wait()
		signal.alarm(0)
		self.completed = True
	except:
		try:
			self.process.terminate()
		except:
			pass
		self.completed = False
		self.exception = True
        return self.completed

    @property
    def returncode(self):
        return self.process.returncode
