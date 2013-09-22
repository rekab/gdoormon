#!/usr/bin/python

import cgi
import clientmonitor
import leasemonitor
import logging
import re
import shelve
import subprocess
import BaseHTTPServer

SERVER_PORT = 2020
ARP = '/usr/sbin/arp'

class Error(Exception):
  pass


class CannotGetIp(Error):
  pass


def GetMacForIp(ip):
  l = logging.getLogger('GetMacForIp')
  cmd = [ARP, '-n', ip]
  cmd_str = ' '.join(cmd)
  l.log(logging.INFO, 'running: %s', cmd_str)
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  (stdout, stderr) = p.communicate()
  if p.returncode != 0:
    error = 'cmd returned %d: %s' % (p.returncode, cmd_str)
    l.log(logging.ERROR, error)
    raise CannotGetIp(error)
  lines = stdout.split('\n')
  if len(lines) != 3:
    error = 'cmd returned: %s' % lines
    l.log(logging.ERROR, error)
    raise CannotGetIp(error)
  parts = re.split(r'\s+', lines[1])
  return parts[2]


class RegistrationHandler(BaseHTTPServer.BaseHTTPRequestHandler):

  def do_POST(self):
    ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
    if ctype == 'multipart/form-data':
      postvars = cgi.parse_multipart(self.rfile, pdict)
    elif ctype == 'application/x-www-form-urlencoded':
      length = int(self.headers.getheader('content-length'))
      postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
    else:
      self.wfile.write('no data posted')
      return
    if ('action' not in postvars or 
        postvars['action'][0] not in ['register', 'unregister']):
      self.send_response(500)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write('ctype=%s length=%s' % (ctype, length))
      self.wfile.write('what? %s' % postvars)
      return
    # TODO: refactor db manipulations to a module
    db = shelve.open(clientmonitor.CLIENT_DB_PATH)
    try:
      ip = self.client_address[0]
      mac = GetMacForIp(ip)
      self.wfile.write('You are ')
      if postvars['action'][0] == 'register':
        db[mac] = ip
      else:
        if mac in db:
          del db[mac]
        self.wfile.write('un')
      self.wfile.write('registered.')
    except CannotGetIp as e:
      self.wfile.write('failed to lookup your mac: %s' % e)
    db.close()

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    try:
      mac = GetMacForIp(self.client_address[0])
      self.wfile.write('FYI your MAC address is: %s' % mac)
      db = shelve.open(clientmonitor.CLIENT_DB_PATH)
      self.wfile.write('<form action="/register" method="post">')
      if mac in db:
        self.wfile.write('You are registered.')
        self.wfile.write('<input type="hidden" name="action" value="unregister">')
        self.wfile.write('<input type="submit" value="unregister">')
      else:
        self.wfile.write('You are not registered.')
        self.wfile.write('<input type="hidden" name="action" value="register">')
        self.wfile.write('<input type="submit" value="register">')
      self.wfile.write('</form>')
    except CannotGetIp as e:
      self.wfile.write('failed to lookup your mac: %s' % e)

if __name__ == '__main__':
  clientmonitor.SetupRootLogger()
  #ssh_conn = ssh.SSHConnection(flags.user, flags.host, flags.port,
  #    flags.password)
  #fetcher = leasemonitor.LeaseFetcher(ssh_conn)
  # TODO: define flags; pass the fetcher to the handler 
  print 'starting up listening on port %s' % SERVER_PORT
  httpd = BaseHTTPServer.HTTPServer(('', SERVER_PORT), RegistrationHandler)
  httpd.serve_forever()
