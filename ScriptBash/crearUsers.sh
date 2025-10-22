#!/bin/bash

#Defino una variable para $1 que seria la lista
#Defino una variable para la expresion regular a utilizar
arch=$1
#regex='^[^:]*:[^:]*:[^:]*:(si|no):/bin/(bash|sh|zsh)$'
#Modifico la variable de expresion regular agregando '[^[:space:]]+' porque asi me aseguro de que los campos de username y dir home no tengan espacios
regex='^[^:][^[:space:]]+*:[^:]*:[^:][^[:space:]]+*:(si|no):/bin/(bash|sh|zsh)$'
#Se chequea que los parametros sean minimo 1 y maximo 3
if [ $# -lt 1 ]; then
	echo "Debe usar minimo 1 parametro (el archivo con la lista de usuarios)">&2
	exit 0
fi

if [ $# -gt 3 ]; then
	echo "Se aceptan maximo 3 parametros (el primero es la lista de usuarios, los otros 2 son modificadores)">&2
	exit 1
fi

#Chequeo que el archivo exista
if [ ! -f $arch ];then
	echo "El archivo: $arch no existe">&2
	exit 2
fi

#Chequeo que el archivo lista sea un archivo regular
if [ ! -f $arch ]; then
	echo "El parametro: $arch no es un archivo regular">&2
	exit 3
fi

#Chequeo que tenga permisos para leer el archivo
if [ ! -r $arch ]; then
	echo "No tengo permisos de lectura sobre: $arch">&2
       	exit 4	
fi

#Se compara cantidad de lineas con la cantidad de lineas validas
#Las lineas validas son aquellas que coincidan con la expresion regular
#Lo que estoy haciendo es chequear la sintaxis de la lista
totlineas=$(cat $arch | wc -l)
validas=$(grep -Ec $regex $arch)
novalidas=$(grep -Env $regex $arch)

if [ ! $totlineas -eq $validas ]; then
	echo ""	
  	echo "Se detectaron errores en la sintaxis de la lista">&2
  	echo "Errores detectados: $(($totlineas - $validas))">&2
	echo ""
  	echo -e "Lineas invalidas: \n$novalidas">&2
  	echo ""
  	echo "Revise la sintaxis de la lista y no deje lineas en blanco">&2
  	exit 5
fi

#Defino opciones por defecto
opdefcom="Comentario por defecto"
opdefhome="/home/$c1"
#La variable $opdefcrearhome la uso tanto como opcion por defecto como tambien en caso de tener que crear el home si en la lista aparece la opcion 'si' en el campo 4
opdefcrearhome="-m"
opdefshell="/bin/bash"

#Ahora debo recorrer la lista para poder ver si hay campos vacios
#Modificar la variable IFS me permite que el for no salte de linea cuando encuentre espacios. En vez de separar por espaciosi, tab y saltos de linea, ahora IFS solo separa por saltos de linea

#el if -z funciona como un test -z, evalua si la variable esta vacia
IFS=$'\n'
for i in $(cat $arch); do
	# c1 es el nombre del usuario, c2 es comentario, c3 es dir home, c4 es si crea o no el home, c5 es la shell
        c1=$(echo "$i" | cut -d: -f1)
	c2=$(echo "$i" | cut -d: -f2)
	c3=$(echo "$i" | cut -d: -f3)
	c4=$(echo "$i" | cut -d: -f4)
	c5=$(echo "$i" | cut -d: -f5)
	#Mediante varios if voy detectando los campos vacios y agregando a los mismos las opciones por defecto	
	if [ -z $c2 ]; then
		c2=$opdefcom
	fi
	
	if [ -z $c3 ]; then
		c3=$opdefhome
	fi
	#Si $c4 esta vacio o es igual a 'si' voy a asignar que cree el home
	#Hago un else que corresponde a si el campo 4 dice 'no', para sustituir el 'no' por vacio
	if [ -z $c4 ] || [ "$c4" = "si" ]; then
		c4="$opdefcrearhome"
	else
		c4=""
	fi

	if [ -z $c5 ]; then
		c5=$opdefshell
	fi
	
	echo "useradd $c1 -c '$c2' -d $c3 $c4 -s $c5"
done

