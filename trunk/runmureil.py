import mureilbuilder
import sys, time

start = time.time()

master = mureilbuilder.build_master(sys.argv[1:])

master.run()

print 'GA calc time: %.2f seconds' % (time.time() - start)
