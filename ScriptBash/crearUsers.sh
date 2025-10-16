#!/bin/bash

#El script recorre una lista pasada como primer parametro y crea los usuarios correspondientes

#Defino opciones por defecto para campos vacios
opdefcom="Comentario por defecto"
opdefhome="/home/$user"
opdefcrearhome=True
opdefshell="/bin/bash"

if [ $# -lt 1 ]; then
	echo "Debe usar minimo 1 parametro (el archivo con la lista de usuarios)"
	exit 0
fi

if [ $# -gt 3 ]; then
	echo "Se aceptan maximo 3 parametros (el primero es la lista de usuarios, los otros 2 son modificadores)"
	exit 1
fi

if [ $(wc -c < $1) -lt 1 ] ; then
	echo "El archivo/lista pasado como parametro {$1} esta vacio"
fi
