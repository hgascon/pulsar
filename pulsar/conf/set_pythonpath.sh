# To add the different modules to the PYTHONPATH
# run "$> source set_pythonpath" from the shell

basedir=$PWD
cuckoo="$basedir/cuckoo"
lens="$basedir/lens"
fuzzer="$basedir/fuzzer"
harry="$basedir/harry"
prisma="$basedir/prisma"
model="$basedir/model"

echo "Adding modules to PYTHONPATH..."
export PYTHONPATH=$PYTHONPATH:$cuckoo:$lens:$fuzzer:$harry:$prisma:$model:/usr/local/lib/python2.7/site-packages
