#/bin/sh
ROOT='YOUR_ROOT_DIRECTORY_HERE' # Directory where WebVectores resides
DIR=$ROOT"/tmp/"

if [ "$(ls -A $DIR)" ]; then
    for f in $DIR/*.gz
	do
	    mv $f $ROOT/training/
	    break
	done
    filename=$(basename $f)
    touch $ROOT/training/$filename.training
    /usr/local/python/bin/python2.7 $ROOT/scripts/train_model.py $ROOT/training/$filename
    mv $ROOT/training/$filename $ROOT/trained
    rm $ROOT/training/$filename.training
    ln -s $ROOT/trained/*.model $ROOT/static/models/
else
    echo "$DIR is empty"
fi



