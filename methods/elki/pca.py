'''
  @file pca.py
  @author Erich Schubert
  @author Marcus Edel -- original weka version

  Class to benchmark the ELKI Principal Components Analysis method.

  TODO: the measured time currently includes the time to parse the data.
  Since PCA is not a streaming filter, we could get the actually processing time seperately.
'''

import os
import sys
import inspect

# Import the util path, this method even works if the path contains symlinks to
# modules.
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(
  os.path.split(inspect.getfile(inspect.currentframe()))[0], "../../util")))
if cmd_subfolder not in sys.path:
  sys.path.insert(0, cmd_subfolder)

from log import *
from profiler import *

import subprocess
import re
import collections

'''
This class implements the Principal Components Analysis benchmark.
'''
class PCA(object):

  '''
  Create the Principal Components Analysis benchmark instance.

  @param dataset - Input dataset to perform PCA on.
  @param timeout - The time until the timeout. Default no timeout.
  @param path - Path to the mlpack executable.
  @param verbose - Display informational messages.
  '''
  def __init__(self, dataset, timeout=0, path=os.environ["JAVAPATH"],
      verbose=True):
    self.verbose = verbose
    self.dataset = dataset
    self.path = path
    self.timeout = timeout

  '''
  Given an input dict of options, return a string that can be given to the
  program.
  '''
  def process_options(self, options):
    opts = []
    if "whiten" in options:
      opts += ["-dbc.filter", "normalization.columnwise.AttributeWiseVarianceNormalization,transform.GlobalPrincipalComponentAnalysisTransform"]
      options.pop("whiten")
    else:
      opts += ["-dbc.filter", "transform.GlobalPrincipalComponentAnalysisTransform"]
    if "new_dimensionality" in options:
      opts += ["-globalpca.filter", "FirstNEigenPairFilter", "-pca.filter.n", str(options.pop("new_dimensionality"))]

    if len(options) > 0:
      Log.Fatal("Unknown parameters: " + str(options))
      raise Exception("unknown parameters")

    return opts

  '''
  Perform Principal Components Analysis. If the method has been successfully 
  completed return the elapsed time in seconds.

  @param options - Extra options for the method.
  @return - Elapsed time in seconds or a negative value if the method was not 
  successful.
  '''
  def RunMetrics(self, options):
    Log.Info("Perform PCA.", self.verbose)

    cmd = ["java", "-jar", self.path + "elki.jar", "cli", "-time", "-dbc.in", self.dataset,
        "-algorithm", "NullAlgorithm", "-resulthandler", "DiscardResultHandler"] + self.process_options(options)

    # Run command with the nessecary arguments and return its output as a byte
    # string. We have untrusted input so we disable all shell based features.
    try:
      s = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=False,
          timeout=self.timeout)
    except subprocess.TimeoutExpired as e:
      Log.Warn(str(e))
      return -2
    except Exception as e:
      Log.Fatal("Could not execute command: " + str(cmd))
      return -1

    # Datastructure to store the results.
    metrics = {}

    # Parse data: runtime.
    timer = self.parseTimer(s)

    if timer != -1:
      metrics['Runtime'] = timer.total_time

      Log.Info(("total time: %fs" % (metrics['Runtime'])), self.verbose)

    return metrics

  '''
  Parse the timer data form a given string.

  @param data - String to parse timer data from.
  @return - Namedtuple that contains the timer data or -1 in case of an error.
  '''
  def parseTimer(self, data):
    # Compile the regular expression pattern into a regular expression object to
    # parse the timer data.
    pattern = re.compile(r""".*?datasource[^\s]*\.load:\s*(?P<total_time>\d+)\s*ms.*?""", re.VERBOSE|re.MULTILINE|re.DOTALL)

    match = pattern.match(data.decode())
    if not match:
      Log.Fatal("Can't parse the data: wrong format")
      return -1
    else:
      # Create a namedtuple and return the timer data.
      timer = collections.namedtuple("timer", ["total_time"])

      if match.group("total_time").count(".") == 1:
        return timer(float(match.group("total_time")) / 1000.)
      else:
        return timer(float(match.group("total_time").replace(",", ".")) / 1000.)
