#!/usr/bin/python
"""AirVision and ImageMagick-based garage door open detector."""

import glob
import logging
import operator
import os
import math
import re
import shutil
import subprocess
import tempfile
import time
import Image
import ImageChops


NUM_SAMPLES = 2
CURL = '/usr/bin/curl'
CONVERT = '/usr/bin/convert'
COMPARE = '/usr/bin/compare'
TESSERACT = '/usr/bin/tesseract'

DOOR_CLOSED_IMAGES_GLOB = ''
DOOR_OPEN_IMAGES_GLOB = ''
#DOOR_CLOSED_IMAGES_GLOB = 'comparison-images/negative/*-cropped.jpg'
#DOOR_OPEN_IMAGES_GLOB = 'comparison-images/positive/*-cropped.jpg'

AIRCAM_URL = 'https://aircam-front/snapshot.cgi?chan=0'
ROTATE_DEGREES = -5
#CROP_GEOMETRY = '120x85+1150+270'

# geometry and args for two lines of text
CROP_GEOMETRY = '125x83+1165+285'
EDGE_RADIUS = 10
TESSERACT_PSM = ''

# geometry and args for one line of text
#CROP_GEOMETRY = '125x41+1165+285'
#TESSERACT_PSM = '-psm 8'

SNAPSHOT_BASENAME = 'snapshot'
OCR_OUT_BASENAME = 'ocr'


class Error(Exception):
  pass

class CommandFailed(Error):
  pass


class CheckedCommandRunner(object):
  def __init__(self):
    self._log = logging.getLogger('gdoormon-command')

  def Run(self, command):
    """Run a command.

    Args:
      command: string, command to run
    Raises:
      CommandFailed: if the command returned non-zero
    """
    self._log.log(logging.INFO, 'running: %s', command)
    exit_status = os.system(str(command))
    self._log.log(logging.INFO, 'command exit status: %d', exit_status)
    if exit_status != 0:
      raise CommandFailed('"%s" returned %d' % (str(command), exit_status))


class Command(object):
  def __init__(self):
    self._working_dir = None

  def SetWorkingDir(self, tmpdir):
    self._working_dir = tmpdir

  def GetWorkingDir(self):
    return self._working_dir


class SnapshotCommand(Command):
  def GetSnapshotPath(self):
    return os.path.join(self.GetWorkingDir(), '%s.jpg' % SNAPSHOT_BASENAME)

  def Run(self, runner):
    """Run.

    Args:
      runner: CheckedCommandRunner
    """
    runner.Run(self.GetCommand())

  def GetCommand(self):
    raise NotImplemented('child classes must implement this method')


class AircamSnapshotFetcher(SnapshotCommand):
  def __init__(self, aircam_url=AIRCAM_URL, curl=CURL):
    SnapshotCommand.__init__(self)
    self._aircam_url = aircam_url
    self._curl = curl

  def GetCommand(self):
    return '%s -k %s > %s' % (self._curl, self._aircam_url,
        self.GetSnapshotPath())


class ImageRotator(SnapshotCommand):
  # TODO: use deskew
  def __init__(self, rotate_degrees=ROTATE_DEGREES, convert=CONVERT):
    SnapshotCommand.__init__(self)
    self._rotate_degrees = rotate_degrees
    self._convert = convert

  def GetCommand(self):
    return '%s -rotate %s %s %s' % (self._convert,
        self._rotate_degrees, self.GetSnapshotPath(), self.GetSnapshotPath())


class ImageCropper(SnapshotCommand):
  def __init__(self, geometry=CROP_GEOMETRY, convert=CONVERT):
    SnapshotCommand.__init__(self)
    self._geometry = geometry
    self._convert = convert

  def GetCommand(self):
    return '%s -crop %s %s %s' % (self._convert,
        self._geometry, self.GetSnapshotPath(), self.GetSnapshotPath())


class ImageEdgeDetection(SnapshotCommand):
  def __init__(self, radius=EDGE_RADIUS, convert=CONVERT):
    SnapshotCommand.__init__(self)
    self._radius = radius
    self._convert = convert

  def GetCommand(self):
    return '%s -edge %s %s %s' % (self._convert,
        self._radius, self.GetSnapshotPath(), self.GetSnapshotPath())


class TextOcr(SnapshotCommand):
  def __init__(self, ocr_basename=OCR_OUT_BASENAME, psm_arg=TESSERACT_PSM,
      tesseract=TESSERACT):
    SnapshotCommand.__init__(self)
    self._ocr_basename = ocr_basename
    self._psm_arg = psm_arg
    self._tesseract = tesseract

  def GetOcrOutputPath(self):
    return os.path.join(self.GetWorkingDir(), self._ocr_basename)

  def GetCommand(self):
    return '%s %s %s %s' % (self._tesseract, self._psm_arg,
        self.GetSnapshotPath(), self.GetOcrOutputPath())


class TextOcrOutputCheck(object):
  def __init__(self, ocr_out=OCR_OUT_BASENAME):
    self._ocr_out = ocr_out
    self._log = logging.getLogger('ocr')

  def Check(self, working_dir):
    """Return a score."""
    ocr_basename = '%s.txt' % self._ocr_out
    ocr_path = os.path.join(working_dir, ocr_basename)
    # Test if the file has text
    with open(ocr_path, 'r') as text:
      msg = text.read().replace('\n', '')
      self._log.log(logging.DEBUG, 'text=%s', msg)
      if re.search('[GargeDOoR]{2,}', msg):
        return 100
      return -100


class ImageComparisonCheck(object):
  def __init__(self, source_image_path, weight, compare=COMPARE,
      snapshot_basename=SNAPSHOT_BASENAME):
    """Constructor.

    Args:
      source_image_path: path to an image to comare to
      weight: multiplier to apply to the RMS score
    """
    self._src_path = source_image_path
    self._source_hist = Image.open(source_image_path).histogram()
    self._weight = weight
    self._compare = compare
    self._snapshot_basename = snapshot_basename
    self._log = logging.getLogger('img-cmp')

class ImageRMSECheck(ImageComparisonCheck):
  def Check(self, working_dir):
    comparison_image_path = os.path.join(
        working_dir, '%s.jpg' % self._snapshot_basename)
    other_hist = Image.open(comparison_image_path).histogram()
    # http://stackoverflow.com/questions/1927660/compare-two-images-the-python-linux-way
    rms = math.sqrt(reduce(operator.add,
          map(lambda a,b: (a-b)**2, self._source_hist, other_hist))/len(self._source_hist))
    # If < 100, it's probably a match. If > 100, it's probably not a match.
    score = float(self._weight) * (100.0 - rms)
    self._log.log(logging.DEBUG, 'source=%s rms=%s score=%s', self._src_path, rms, score)
    return score


# TODO: make the sign bright green, check the green channel histogram
class ImageCompareRMSECheck(ImageComparisonCheck):
  def Check(self, working_dir):
    comparison_image_path = os.path.join(
        working_dir, '%s.jpg' % self._snapshot_basename)
    cmd = [self._compare, '-metric', 'RMSE', comparison_image_path, self._src_path, 'null']
    cmd_str = ' '.join(cmd)
    self._log.log(logging.DEBUG, 'running: %s', cmd_str)
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    if p.returncode != 0:
      raise CommandFailed('"%s" failed with exit code: %d' % (cmd_str, p.returncode))
    m = re.match(r'[\d\.]+\s+\(([\d\.]+)\)', stderr)
    if not m:
      self._log.log(logging.ERROR, 'failed to parse "%s"' % stderr)
      return 0
    score = (1.0 - float(m.group(1))) * self._weight
    self._log.log(logging.DEBUG, 'score=%s', score)
    return score


class GarageDoorChecker(object):
  def __init__(self, runner, img_cmds, checks, cleanup=True):
    """Constructor.

    Args:
      runner: CheckedCommandRunner object
      img_cmds: list of SnapshotCommand objects
      checks: list of check objects
      cleanup: cleanup temp files (default: True)
    """
    self._runner = runner
    self._img_cmds = img_cmds
    self._checks = checks
    self._cleanup = cleanup
    self._log = logging.getLogger('gdoormon-checker')

  def IsDoorOpen(self):
    tmpdir = tempfile.mkdtemp()
    try:
      for cmd in self._img_cmds:
        cmd.SetWorkingDir(tmpdir)
        cmd.Run(self._runner)
      score = 0
      for check in self._checks:
        score += check.Check(tmpdir)
        #self._log.log(logging.DEBUG, 'temp score=%d', score)
      self._log.log(logging.INFO, 'door open score=%d', score)
      return score > 0
    finally:
      if self._cleanup:
        self._log.log(logging.DEBUG, 'cleaning up %s', tmpdir)
        shutil.rmtree(tmpdir)
      else:
        self._log.log(logging.INFO, 'not cleaning up files in %s', tmpdir)


class GarageDoorMonitor(object):

  def __init__(self, checker, num_samples=NUM_SAMPLES):
    self._checker = checker
    self._prev_samples = []
    self._log = logging.getLogger('gdoormon')
    self._num_samples = num_samples
    self._door_open = None

  def Check(self):
    """Check if the door is open.

    Returns:
      True if the door is probably open, False otherwise.
    """
    self._prev_samples.append(self._checker.IsDoorOpen())
    # cut the length
    self._prev_samples = self._prev_samples[-self._num_samples:]
    # return true if all samples agree
    if len([s for s in self._prev_samples if s]) == len(self._prev_samples):
      self._log.log(logging.INFO, 'door is open')
      self._door_open = True
    else:
      self._log.log(logging.INFO, 'door is NOT open')
      self._door_open = False
    return self._door_open

  def IsDoorOpen(self):
    return self._door_open


def GetImageCommands():
  fetch = AircamSnapshotFetcher()
  rotate = ImageRotator()
  crop = ImageCropper()
  edge = ImageEdgeDetection()
  ocr = TextOcr()
  return [fetch, rotate, crop, edge, ocr]


def GetMonitor():
  runner = CheckedCommandRunner()
  img_cmds = GetImageCommands()
  image_checks = [TextOcrOutputCheck()]
  for img in glob.glob(DOOR_CLOSED_IMAGES_GLOB):
    image_checks.append(ImageRMSECheck(img, -.5))
    image_checks.append(ImageCompareRMSECheck(img, -100))
  for img in glob.glob(DOOR_OPEN_IMAGES_GLOB):
    image_checks.append(ImageRMSECheck(img, .5))
    image_checks.append(ImageCompareRMSECheck(img, 100))
  checker = GarageDoorChecker(runner, img_cmds, image_checks, cleanup=True)
  return GarageDoorMonitor(checker)


if __name__ == '__main__':
  import consolelog
  consolelog.SetupRootLogger()

  monitor = GetMonitor()
  log = logging.getLogger()
  while True:
    log.log(logging.INFO, 'checking if door is open')
    if monitor.Check():
      log.log(logging.INFO, 'yes: open')
    else:
      log.log(logging.INFO, 'no: not open')
    log.log(logging.INFO, 'sleeping 30s')
    time.sleep(30)
