import os
import smtplib

# ref: http://www.tutorialspoint.com/python/python_sending_email.htm
def send_email(name_from, email_from, name_to, email_to, subject, msg, smtp_server="smtp.ncsu.edu"):
        sender = email_from
        receivers = [email_to]

        message = "From: %s <%s>\nTo: %s <%s>\nSubject: %s\n\n%s" % (name_from, email_from, name_to, email_to, subject, msg)


        try:
                smtpObj = smtplib.SMTP(smtp_server)
                smtpObj.sendmail(sender, receivers, message)
        except Exception:
                return False
        return True

def locate_makefile_dir(dest):
        if "makefile" in [x.lower() for x in os.listdir(dest)]:
                return dest

        for f in os.listdir(dest):
                if os.path.isdir(os.path.join(dest, f)):
                        result = locate_makefile_dir(os.path.join(dest, f))
                        if result is not None:
                                return result

        return None

def subdirs(d):
    return filter(os.path.isdir, [os.path.join(d,f) for f in os.listdir(d)])
