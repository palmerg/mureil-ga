#
#
# Copyright (C) University of Melbourne 2012
#
#
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#
import tools.mureilbuilder as mureilbuilder
import tools.mureilexception as mureilexception
import sys
import logging

logger = logging.getLogger(__name__)

def runmureil(flags):
    master = None
    try:
        master = mureilbuilder.build_master(flags)
    except mureilexception.MureilException as me:
        handle_exception(me)

    if master:    
        try:
            master.run()
        except mureilexception.MureilException as me:
            handle_exception(me)
        except Exception as me:
            logger.critical('Execution stopped on unhandled exception',
                exc_info=me)
        finally:
            return master.finalise()


def handle_exception(me):
    # More information than this is available in the exception
    logger.critical('Execution stopped on ' + me.__class__.__name__)
    logger.critical(me.msg)


if __name__ == '__main__':
    runmureil(sys.argv[1:])
