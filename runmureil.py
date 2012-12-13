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

    if master is not None:    
        try:
            master.run()
        except mureilexception.MureilException as me:
            handle_exception(me)
        finally:
            master.finalise()


def handle_exception(me):
    # More information than this is available in the exception
    logger.critical('Execution stopped on ' + me.__class__.__name__)
    logger.critical(me.msg)


if __name__ == '__main__':
    runmureil(sys.argv[1:])
