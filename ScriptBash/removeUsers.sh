#!/bin/bash
regex='^[^:][a-zA-Z0-9_-]*:[^:]*:[a-zA-Z0-9_/-]*[^[:space:]:]*:(SI|NO|si|no)?:[a-zA-Z0-9/_-]*?'

for i in $( egrep $regex $1 | cut -d: -f1 ); do
	if  userdel $i ; then
		echo "Eliminado: $i"
	else
		echo "no se elimino $i"
	fi
done
