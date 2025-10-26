#!/bin/bash
regex='^[^:][^[:space:]]+*:[^:]*:[^:][^[:space:]]+*:(si|no):/bin/(bash|sh|zsh)$'

for i in $( egrep $regex $1 | cut -d: -f1 ); do
	userdel $i
done
