""" ********** getFiles.py **********

Author: Michael Giansiracusa
Email: giansiracumt@ornl.gov

Web Tools Contact: Ranjeet Devarakonda zzr@ornl.gov

Purpose:
    This tool supports downloading files using the ARM Live Data Webservice
Requirements:
    This tool requires python3, requests, and loguru package
"""
from __future__ import (division, print_function, absolute_import,
                        unicode_literals)
try:
    from future_builtins import ascii, filter, hex, map, oct, zip
except:
    pass
import sys
if sys.version_info.major > 2:
    xrange = range
import argparse
import json
import requests
import sys
import os
from loguru import logger

HELP_DESCRIPTION = """
*************************** ARM LIVE UTILITY TOOL ****************************
This tool will help users utilize the ARM Live Data Webservice to download ARM data.
This programmatic interface allows users to query and automate machine-to-machine
downloads of ARM data. This tool uses a REST URL and specific parameters (saveData,
query), user ID and access token, a datastream name, a start date, and an end date,
and data files matching the criteria will be returned to the user and downloaded.

By using this web service, users can setup cron jobs and automatically download data from
/data/archive into their workspace. This will also eliminate the manual step of following
a link in an email to download data. All other data files, which are not on the spinning
disk (on HPSS), will have to go through the regular ordering process. More information
about this REST API and tools can be found at: https://adc.arm.gov/armlive/#scripts

To login/register for an access token visit: https://adc.arm.gov/armlive/livedata/home.
----------------------------******************************************************************************
"""
EXAMPLE = """
Example:
python getFiles.py -u userName:XXXXXXXXXXXXXXXX -ds sgpmetE13.b1 -s 2017-01-14 -e 2017-01-20
"""

def parse_arguments():
    """Parse command line arguments using argparse

    :return:
        Two Namespace object that have an attribute for each command line argument.
        The first return arg contains expected command line flags and arguments.
        The second return arg contains unexpected command line flags and arguments.
    """
    parser = argparse.ArgumentParser(description=HELP_DESCRIPTION, epilog=EXAMPLE,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    required_arguments = parser.add_argument_group("required arguments")

    required_arguments.add_argument("-u", "--user", type=str, dest="user", required=True,
                                    help="The user's ARM ID and access token, separated by a colon."
                                         "Obtained from https://adc.arm.gov/armlive/livedata/home")
    required_arguments.add_argument("-ds", "--datastream", type=str, dest="datastream",
                                    help="Name of the datastream. The query service type allows the"
                                         "user to enter a DATASTREAM property that's less specific,"
                                         "and returns a collection of data files that match the"
                                         "DATASTREAM property. For example: sgp30ebbrE26.b1")

    parser.add_argument("-s", "--start", type=str, dest="start",
                        help="Optional; start date for the datastream. "
                             "Must be of the form YYYY-MM-DD")
    parser.add_argument("-e", "--end", type=str, dest="end",
                        help="Optional; end date for the datastream. "
                             "Must be of the form YYYY-MM-DD")
    parser.add_argument("-o", "--out", type=str, dest="output", default='',
                        help="Optional; full path to directory where you would like the output"
                             "files. Defaults to folder named after datastream in current working"
                             "directory.")
    parser.add_argument("-T", "--test", action="store_true", dest="test",
                        help="Optional; flag that enables test mode. When in test mode only the"
                             "query will be run.")
    parser.add_argument("-D", "--Debug", action="store_true", dest="debug",
                        help="Optional; flag that enables debug printing")

    cli_args, unknown_args = parser.parse_known_args()

    if len(sys.argv) <= 1 or not (cli_args.user and cli_args.datastream):
        parser.print_help()
        parser.print_usage()
        exit(1)

    return cli_args, unknown_args

def main():
    cli_args, unknown_args = parse_arguments()
    """ main armlive automation script

    :param cli_args:
        A argparse.Namespace object with an attribute for each expected command line argument.
    :return:
        None
    """
    # set logging level
    logger.remove(0)
    logger.level('CRITICAL', color='<r>')
    logger.level('WARNING', color='<y>')
    logger.level('DEBUG', color='<lm>')
    logger.level('INFO', color='<le>')
    if cli_args.debug or cli_args.test:
        logger.add(sys.stdout, colorize=True, level='DEBUG')
    else:
        logger.add(sys.stdout, colorize=True, level='INFO',
                   format='<e>{time:YYYY:MM:D:HH:mm:ss}</e> |<le>{level}</le>| <g>{message}</g>')
    # default start and end are empty
    start, end = '', ''
    # start and end strings for query_url are constructed if the arguments were provided
    if cli_args.start:
        start = "&start={}".format(cli_args.start)
    if cli_args.end:
        end = "&end={}".format(cli_args.end)
    # build the url to query the web service using the arguments provided
    query_url = 'https://adc.arm.gov/armlive/livedata/query?user={0}&ds={1}{2}{3}&wt=json'\
        .format(cli_args.user, cli_args.datastream, start, end)

    logger.debug("Getting file list using query url:\n\t{0}".format(query_url))
    # get url response, read the body of the message, and decode from bytes type to utf-8 string
    response_body = requests.get(query_url).text

    # if the response is an html doc, then there was an error with the user
    if response_body[1:14] == "!DOCTYPE html":
        logger.warning("Error with user. Check username or token.")
        exit(1)
    # parse into json object
    response_body_json = json.loads(response_body)
    logger.debug("response body:\n{0}\n".format(json.dumps(response_body_json, indent=True)))

    # construct output directory
    if cli_args.output:
        # output files to directory specified
        output_dir = os.path.join(cli_args.output)
    else:
        # if no folder given, add datastream folder to current working dir to prevent file mix-up
        output_dir = os.path.join(os.getcwd(), cli_args.datastream)

    # not testing, response is successful and files were returned
    if not cli_args.test:
        num_files = len(response_body_json["files"])
        if response_body_json["status"] == "success" and num_files > 0:
            for fname in response_body_json['files']:
                logger.info("[DOWNLOADING] {}".format(fname))
                # construct link to web service saveData function
                save_data_url = "https://adc.arm.gov/armlive/livedata/saveData?user={0}&file={1}"\
                    .format(cli_args.user, fname)
                logger.debug("Using link: {1}".format(fname, save_data_url))

                output_file = os.path.join(output_dir, fname)
                # make directory if it doesn't exist
                if not os.path.isdir(output_dir):
                    os.makedirs(output_dir)
                # create file and write bytes to file
                with open(output_file, 'wb') as open_file:
                    open_file.write(requests.get(save_data_url).content)
                    logger.success("[DOWNLOADED] {}".format(fname))
                logger.debug("file saved to --> {}\n".format(output_file))
        else:
            logger.warning("No files returned or url status error.\n"
                           "Check datastream name, start, and end date.")
    else:
        logger.debug("*** Files would have been downloaded to directory:\n----> {}".format(output_dir))

if __name__ == "__main__":
    main()

