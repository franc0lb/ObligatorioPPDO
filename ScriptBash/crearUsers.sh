#!/bin/bash

#Defino una variable para $1 que seria la lista
#Defino una variable para la expresion regular que utilizo para verificar que haya 4 campos y otra para que la sintaxis de esos 4 campos
arch=$1
#la regex de la variable regex chequea que el nombre de usuario no este vacio y que contenga caracteres validos
#que comentario sea cualquier cosa menos 2 puntos,que el home sea cualquier cosa sin espacios
#que el campo de crear home pueda ser si o no en mayusculas/minusculas 0 o 1 vez
#y que el campo de la shell pueda ser algo que arranque con barra, siga con caracteres, numeros y guiones bajos y altos, se repita x veces, 0 o 1 vez y termine la linea
regex='^[^:][a-zA-Z0-9_-]*:[^:]*:(/[a-zA-Z0-9/_-]*)?:(SI|NO|si|no)?:(/[a-zA-Z0-9/_-]*)?$'
regexCampos='^[^:]*:[^:]*:[^:]*:[^:]*:[^:]*$'
#Se chequea que los parametros sean minimo 1 y maximo 4, siendo el 4 una contraseña en caso de que el 3 sea -c
if [ $# -lt 1 ]; then
	echo "Debe usar minimo 1 parametro (el archivo con la lista de usuarios)">&2
	exit 0
fi

if [ $# -gt 4 ]; then
	echo "Se aceptan maximo 4 parametros: La lista de los usuarios, -c para asignar una contraseña, la contraseña, y -i para mostrar la creacion del usuario">&2
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


#Se compara cantidad de lineas totales con la cantidad de lineas validas segun la expresion de la variable regexCampos para chequear que haya 5 campos
totlineas=$(cat $arch | wc -l)
validas1=$(grep -Ec $regexCampos $arch)
novalidas1=$(grep -Env $regexCampos $arch)

if [ ! $totlineas -eq $validas1 ]; then
  	echo "Se detectaron errores en la sintaxis de la lista">&2
  	echo "Errores detectados: $(($totlineas - $validas1))">&2
	echo "">&2
  	echo -e "Lineas invalidas: \n$novalidas1">&2
  	echo "">&2
  	echo "Revise la sintaxis de la lista y no deje lineas en blanco">&2
	echo "Recuerde que son 5 campos en total, por ende las lineas deben contener 4 ':' como máximo">&2
	echo "Recuerde que el primer campo no puede estar vacío ya que es el nombre del usuario">&2
  	exit 5
fi

#Se compara la cantidad de lineas totales con la cantidad de lineas validas segun la expresion de la variable regex
validas2=$(grep -Ec $regex $arch)
novalidas2=$(grep -Env $regex $arch)

if [ ! $totlineas -eq $validas2 ]; then
        echo ""
        echo "Se detectaron errores en la sintaxis de la lista">&2
        echo "Errores detectados: $(($totlineas - $validas2))">&2
	echo "Revise la sintaxis de la lista">&2
	echo "">&2
	echo "Recuerde que el nombre del usuario no puede contener espacios ni caracteres raros">&2
	echo "Recuerde que el home del usuario no puede contener espacios ni caracteres raros">&2
	echo "Recuerde que el shell del usuario no puede contener espacios ni caracteres raros">&2
	echo "Recuerde que el shell y el home en caso de existir deben empezar con '/'">&2
        echo "">&2
        echo -e "Lineas invalidas: \n$novalidas2">&2
        echo "">&2
        exit 20
fi

#Aca chequeo que no se repita el usuario en la lista, el cut me da el primer campo, el sort me ordena la lista, el uniq -d me da los repetidos
#el if testea que $userRepetidos no esté vacío, si es cierto entonces hay usuarios repetidos, y se procede a mostrar esas lineas por pantalla
userRepetido=$(cut -d: -f1 "$arch" | sort | uniq -d)
if test -n "$userRepetido"; then
	userRepetido=$(grep -En "^$userRepetido:" "$arch")
	echo "Error de sintaxis, hay usuarios repetidos en la lista">&2
	echo "Lineas no validas:">&2
	echo "">&2
	echo "$userRepetido">&2
	exit 21
fi

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
if [ $passTrue -eq 0 ] && [ $mostrar -eq 0 ] && test -n "$3" ; then
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
#En este caso evaluo que si $2 es -i y $3 exista entonces $3 debe ser si o si -c o dar error
if [ "$2" = "-i" ] && [ -n "$3" ]; then
	if [ ! "$3" = "-c" ]; then
		echo "El parametro 3: '$3' no es un modificador valido">&2
		exit 7
	fi
fi

#En este caso estoy evaluando si existe el parametro 4, $4 es solo valido como contraseña si $3 era -c que se evaluó anteriormente, en ese caso $4 sería la contraseña
#El otro caso de validez sería que $4 sea -i luego de que $2 sea -c, porque $3 sería la contraseña, si no se cumple ninguno de esos casos es inválido
if [ "$2" = "-c" ] && [ -n "$4" ]; then
	if [ "$4" = "-i" ]; then
		mostrar=1
	else
		echo "Parametro 4: $4 no es valido">&2
		exit 9
	fi

#Este elif se pone para evaluar cuando $2 no es -c y $3 no es -c, porque en ese caso no hay forma que $4 sea valido
#El [ ! "$3" = "-c" ] permite que no de error si $3 es -c, porque preciso que en ese caso $4 sea valido porque es la contraseña
elif [ ! "$2" = "-c" ] && [ -n "$4" ] && [ ! "$3" = "-c" ]; then	
	echo "Parametro 4: $4 no es valido">&2
	exit 9
fi
#Modificar la variable IFS me permite que el for no salte de linea cuando encuentre espacios
#En vez de separar por espacios, tab y saltos de linea, ahora IFS solo separa por saltos de linea
IFS=$'\n'

#Ahora debo recorrer la lista para poder ver si hay campos vacios
#test -z es para detectar si la variable esta vacia
usuarios_creados=0
for i in $(cat "$arch"); do
        #c1 es el nombre del usuario, c2 es comentario, c3 es dir home, c4 es si crea o no el home, c5 es la shell
	c1=$(echo "$i" | cut -d: -f1)
	c2=$(echo "$i" | cut -d: -f2)
	c3=$(echo "$i" | cut -d: -f3)
	c4=$(echo "$i" | cut -d: -f4)
	c5=$(echo "$i" | cut -d: -f5)
	#Defino opciones por defecto
	opdefcom="Comentario por defecto"
	opdefhome="/home/$c1"
	#La variable $opdefcrearhome la uso tanto como opcion por defecto 
	#como tambien en caso de tener que crear el home si en la lista aparece la opcion 'si' en el campo 4
	opdefcrearhome="-m"
	opdefshell="/bin/bash"

       #Detectar campos vacíos y asignar valores por defecto
	if test -z "$c2"; then
		c2=$opdefcom
	fi

	if test -z "$c3"; then
        	c3="$opdefhome"
	fi

    # Si $c4 está vacío o es igual a 'si', asignar que cree el home
    # Si dice 'no', sustituir por vacío
	if test -z "$c4" || [ "$c4" = "si" ]; then
		c4="$opdefcrearhome"
	else
		c4="-M"
	fi

	if test -z "$c5"; then
		c5=$opdefshell
	fi
	#Evaluo si el user ya existe con el comando id, en ese caso guardo el username en una variable para evaluarlo más adelante y mostrar por pantalla el error
	if id "$c1" &>/dev/null; then
		yaexiste="$c1"
		if [ "$mostrar" = "1" ]; then
			echo "ATENCIÓN: el usuario '$c1' no fue creado porque ya existe" >&2
			echo "">&2
		fi
	fi
	#Evaluo si la opcion -c está activa o no, y en cada caso creo los usuarios según ese criterio
	#Si la variable yaexiste contiene al usuario entonces no lo creo porque ya existe
	if [ "$passTrue" -eq 1 ] && [ ! "$yaexiste" = "$c1" ]; then
		useradd "$c1" -c "$c2" -d "$c3" "$c4" -s "$c5" &>/dev/null
		echo "$pass" | passwd --stdin "$c1" &>/dev/null
		usuarios_creados=$((usuarios_creados+1))
	elif [ "$passTrue" -eq 0 ] && [ ! "$yaexiste" = "$c1" ]; then
        	useradd "$c1" -c "$c2" -d "$c3" "$c4" -s "$c5" &>/dev/null
		usuarios_creados=$((usuarios_creados+1))
	fi
	#Evaluo que el usuario haya sido creado con el comando id como hice anteriormente, pero tambien evaluo la variable $yaexiste.
	#Evaluo esa variable porque si el usuario ya existia no quiero que se ejecute el mensaje de usuario creado con exito etc etc
	#Si $yaexiste no es igual a $c1 pero el comando id da verdadero quiere decir que el usuario no existia y ahora existe, osea fue creado
	#Se evalua también la variable $mostrar para saber si la opción -i está activa o no
	if id "$c1" &>/dev/null && [ ! "$yaexiste" = "$c1" ] && [ "$mostrar" = "1" ]; then
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
	elif [ "$yaexiste" = "$c1" ]; then
		echo -n
	elif [ ! "$yaexiste" = "$c1" ] && [ "$mostrar" = "1" ]; then
                echo "ATENCIÓN: el usuario '$c1' no pudo ser creado"
                echo ""
    	fi
done

echo "Usuarios creados: $usuarios_creados"

