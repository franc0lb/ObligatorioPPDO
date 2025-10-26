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

if [ $# -gt 4 ]; then
	echo "Se aceptan maximo 3 parametros: La lista de los usuarios, -c para asignar una contraseña y -i para mostrar la creacion del usuario">&2
	exit 1
fi

#Chequeo que el archivo exista
if ! test -e $arch ;then
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

#Ahora hago varios if que van a ir detectando las opciones que paso el usuario, para asignar contraseña y/o mostrar la creacion del usuario en pantalla
#Defino variables que en este caso 0 es falso y 1 verdadero, que corresponden a si se ingreso una contraseña con -c y si se debe mostrar la creacion del usuario por pantalla
passTrue=0
mostrar=0
#este primer if testea que el parametro 2 no este vacio
if test -n "$2"; then
    #se testea si es -c y si el parametro 3 esta vacio ya que alli iria la contraseña ingresada	
    if [ "$2" = "-c" ]; then
        if test -z "$3"; then
            echo "Luego del modificador '-c' debe asignar la contraseña por defecto para los usuarios" >&2
            exit 6
        fi
	#en caso de que $3 no haya estado vacio entonces se ingresó el modificador -c y una contraseña
        passTrue=1
        pass="$3"
    #Se hace un elif para el caso de que $2 sea -i y $3 -c
    elif [ "$2" = "-i" ]; then
        if [ "$3" = "-c" ]; then
	    #si $2 es -i y $3 es -c entonces $4 no puede estar vacío porque va la contraseña
            if test -z "$4"; then
                echo "Luego del modificador '-c' debe asignar la contraseña por defecto para los usuarios" >&2
                exit 6
            fi
            passTrue=1
            pass="$4"
            mostrar=1
	#este else se pone para el caso donde $3 no fue -c ni -i
        else
            mostrar=1
        fi
    #este elif evalua para -ic y -ci y que $3 no este vacio
    #$3 puede valer -i en este caso, pero el '-i' se tomará como la contraseña y no como modificador    
    elif [ "$2" = "-ic" ] || [ "$2" = "-ci" ]; then
        if test -z "$3"; then
            echo "Luego del modificador '-c' debe asignar la contraseña por defecto para los usuarios" >&2
            exit 6
        fi
        passTrue=1
        pass="$3"
        mostrar=1
    #este else corresponde al segundo if de todos, porque si $2 no es ni -c, ni -i ni -ic ni -ci entonces no es valido
    else
        echo "El parámetro 2: '$2' no es un modificador válido" >&2
        exit 8
    fi
fi

#Se hace un if para evaluar $3
#Solo evalua $3 si no se manejó ya un caso con -ci/-ic o -c contraseña
if [ $passTrue -eq 0 ] && [ $mostrar -eq 0 ] && test -n "$3"; then
    if [ "$3" = "-c" ]; then
        if test -z "$4"; then
            echo "Luego del modificador '-c' debe asignar la contraseña por defecto para los usuarios" >&2
            exit 6
        else
            passTrue=1
            pass="$4"
        fi
    elif [ "$3" = "-i" ]; then
        mostrar=1
    else
        echo "El parámetro 3: '$3' no es un modificador válido" >&2
        exit 7
    fi
fi

if [ "$2" = "-i" ] && [ -n "$3" ]; then
	if [ ! "$3" = "-c" ]; then
		echo "El parametro 3: '$3' no es un modificador valido">&2
		exit 7
	fi
fi

#Modificar la variable IFS me permite que el for no salte de linea cuando encuentre espacios
#En vez de separar por espacios, tab y saltos de linea, ahora IFS solo separa por saltos de linea
IFS=$'\n'

#Ahora debo recorrer la lista para poder ver si hay campos vacios
#test -z es para detectar si la variable esta vacia

usuarios_creados=0
for i in $(cat "$arch"); do
    # c1 es el nombre del usuario, c2 es comentario, c3 es dir home, c4 es si crea o no el home, c5 es la shell
	c1=$(echo "$i" | cut -d: -f1)
	c2=$(echo "$i" | cut -d: -f2)
	c3=$(echo "$i" | cut -d: -f3)
	c4=$(echo "$i" | cut -d: -f4)
	c5=$(echo "$i" | cut -d: -f5)

    # Detectar campos vacíos y asignar valores por defecto
	if test -z "$c2"; then
		c2=$opdefcom
	fi

	if test -z "$c3"; then
        	c3=$opdefhome
	fi

    # Si $c4 está vacío o es igual a 'si', asignar que cree el home
    # Si dice 'no', sustituir por vacío
	if test -z "$c4" || [ "$c4" = "si" ]; then
		c4="$opdefcrearhome"
	else
		c4=""
	fi

	if test -z "$c5"; then
		c5=$opdefshell
	fi

	if grep -q "^$c1:" /etc/passwd; then
		yaexiste=$c1
		echo "ATENCIÓN: el usuario '$c1' no fue creado porque ya existe" >&2
		echo ""
	fi

	if [ "$passTrue" -eq 1 ]; then
		useradd "$c1" -c "$c2" -d "$c3" $c4 -s "$c5" &>/dev/null
		echo "$pass" | passwd --stdin "$c1" &>/dev/null
	else
        useradd "$c1" -c "$c2" -d "$c3" $c4 -s "$c5" &>/dev/null
	fi

	if id "$c1" &>/dev/null && [ ! "$yaexiste" = "$c1" ]; then
        	echo "Usuario '$c1' creado con éxito con datos indicados:"
 	        echo "Comentario: $c2"
	        echo "Dir home: $c3"
	        if [ -d "$c3" ]; then
                	echo "Asegurado existencia de directorio home: SI"
        	else
                        echo "Asegurado existencia de directorio home: NO"
                fi
                echo "Shell por defecto: $c5"
                echo ""
   	        usuarios_creados=$((usuarios_creados+1))
	elif [ "$yaexiste" = "$c1" ]; then
		echo -n
	else
                echo "ATENCIÓN: el usuario '$c1' no pudo ser creado"
                echo ""
    	fi
done

echo "Usuarios creados: $usuarios_creados"

