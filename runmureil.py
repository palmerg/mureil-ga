import mureilbuilder
import sys, time

start = time.time()

full_config = mureilbuilder.read_config_file(sys.argv[1])
full_config = mureilbuilder.update_from_flags(full_config, sys.argv[2:])

master = mureilbuilder.create_master_instance(full_config)
master.run()

print 'GA calc time: %.2f seconds' % (time.time() - start)
