#/bin/sh
DIR="/home/sites/ling.go.mail.ru/tmp/"
if [ "$(ls -A $DIR)" ]; then
    for f in $DIR/*.gz
	do
	    mv $f /home/sites/ling.go.mail.ru/training/
	    break
	done
    filename=$(basename $f)
    touch /home/sites/ling.go.mail.ru/training/$filename.training
    /usr/local/python/bin/python2.7 /home/sites/ling.go.mail.ru/scripts/train_model.py /home/sites/ling.go.mail.ru/training/$filename
    mv /home/sites/ling.go.mail.ru/training/$filename /home/sites/ling.go.mail.ru/trained
    rm /home/sites/ling.go.mail.ru/training/$filename.training
    ln -s /home/sites/ling.go.mail.ru/trained/*.model /home/sites/ling.go.mail.ru/static/models/
else
    echo "$DIR is empty"
fi



