#!/bin/bash


#Defino opciones por defecto para campos vacios
opdefcom="Comentario por defecto"
opdefhome="/home/$user"
opdefcrearhome=True
opdefshell="/bin/bash"

#Se chequea que los parametros sean minimo 1 y maximo 3
if [ $# -lt 1 ]; then
	echo "Debe usar minimo 1 parametro (el archivo con la lista de usuarios)"
	exit 0
fi

if [ $# -gt 3 ]; then
	echo "Se aceptan maximo 3 parametros (el primero es la lista de usuarios, los otros 2 son modificadores)"
	exit 1
fi

#arch es el primer parametro correspondiente al archivo lista
#regex es una variable que contiene la expresion regular a utilizar
arch=$1
regex='^[^:]*:[^:]*:[^:]*:(si|no):/bin/(bash|sh|zsh)$'

#Se compara cantidad de lineas con la cantidad de lineas validas
#Las lineas validas son aquellas que coincidan con la expresion regular
totlineas=$(cat $arch | wc -l)
validas=$(grep -Ec $regex $arch)
novalidas=$(grep -Env $regex $arch)

if [ $totlineas -eq $validas ]; then
  echo "Todo correcto"
else
  echo "Errores detectados: $(($totlineas - $validas))"
  echo -e "Lineas invalidas: \n$novalidas"
fi

