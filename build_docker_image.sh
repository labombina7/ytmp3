#Generar imagen docker para desplegar en el NAS: 
#ejecutar como sudo
docker buildx build --platform linux/amd64 -t ytmp3:latest .
docker save -o ytmp3.tar ytmp3:latest

chmod 777 ytmp3.tar
cp ytmp3.tar /Volumes/project/mp3d/.